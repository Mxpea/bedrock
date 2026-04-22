import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import AuditLog, InviteCode
from apps.customization.css_validator import validate_advanced_css
from apps.customization.models import AdvancedStyleGrant, AuthorHomepageConfig, CustomCSSRequest
from apps.novels.models import Chapter, Novel

from .models import ContentReport, PlatformSetting, RoastMessage

User = get_user_model()


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "/login/"

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_admin_user()


class SuperAdminRequiredMixin(AdminRequiredMixin):
    def test_func(self):
        user = self.request.user
        return super().test_func() and user.is_superuser


def write_audit(actor, action, target_type="", target_id="", metadata=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id or ""),
        metadata=metadata or {},
    )


def parse_date(raw):
    if not raw:
        return None
    try:
        return timezone.datetime.fromisoformat(raw).date()
    except ValueError:
        return None


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = now.date()
        day_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))

        pending_css = CustomCSSRequest.objects.filter(status=CustomCSSRequest.Status.PENDING).count()
        pending_reports = ContentReport.objects.filter(status=ContentReport.Status.PENDING).count()
        reported_roasts = RoastMessage.objects.filter(status=RoastMessage.Status.REPORTED).count()

        context.update(
            {
                "pending_css": pending_css,
                "pending_reports": pending_reports,
                "reported_roasts": reported_roasts,
                "today_new_users": User.objects.filter(date_joined__gte=day_start).count(),
                "today_new_workspaces": Novel.objects.filter(created_at__gte=day_start, is_deleted=False).count(),
                "today_public_chapters": Chapter.objects.filter(created_at__gte=day_start, is_published=True).count(),
                "today_roasts": RoastMessage.objects.filter(created_at__gte=day_start).count(),
                "recent_workspaces": Novel.objects.filter(is_deleted=False).select_related("author").order_by("-created_at")[:8],
                "recent_public_chapters": Chapter.objects.filter(is_published=True).select_related("novel").order_by("-created_at")[:8],
                "recent_css_requests": CustomCSSRequest.objects.select_related("applicant", "novel").order_by("-created_at")[:8],
            }
        )
        return context


class WorkspaceManageView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/workspaces.html"

    def post(self, request, *args, **kwargs):
        workspace_id = request.POST.get("workspace_id")
        action = request.POST.get("action")
        workspace = get_object_or_404(Novel, id=workspace_id, is_deleted=False)

        if action == "force_private":
            workspace.visibility = Novel.Visibility.PRIVATE
            workspace.save(update_fields=["visibility", "updated_at"])
            messages.success(request, f"已将工作区 {workspace.title} 设置为私密")
        elif action == "toggle_lock":
            workspace.is_locked = not workspace.is_locked
            workspace.save(update_fields=["is_locked", "updated_at"])
            state = "锁定" if workspace.is_locked else "解锁"
            messages.success(request, f"工作区 {workspace.title} 已{state}")
        elif action == "soft_delete":
            workspace.is_deleted = True
            workspace.save(update_fields=["is_deleted", "updated_at"])
            messages.success(request, f"工作区 {workspace.title} 已删除")
        elif action == "disable_preview_link":
            workspace.visibility = Novel.Visibility.PRIVATE
            workspace.save(update_fields=["visibility", "updated_at"])
            messages.success(request, "已强制下线预览链接")
        elif action == "clear_cache":
            cache.clear()
            messages.success(request, "已执行缓存清理（当前为全局缓存级）")

        write_audit(request.user, f"admin.workspace.{action}", "workspace", workspace.id, {"title": workspace.title})
        return redirect("adminpanel:workspaces")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Novel.objects.filter(is_deleted=False).select_related("author")

        keyword = self.request.GET.get("q", "").strip()
        visibility = self.request.GET.get("visibility", "").strip()
        start = parse_date(self.request.GET.get("start"))
        end = parse_date(self.request.GET.get("end"))

        if keyword:
            query_filter = Q(title__icontains=keyword) | Q(author__username__icontains=keyword)
            if keyword.isdigit():
                query_filter = query_filter | Q(id=int(keyword))
            queryset = queryset.filter(query_filter)
        if visibility in {Novel.Visibility.PRIVATE, Novel.Visibility.LINK, Novel.Visibility.PUBLIC}:
            queryset = queryset.filter(visibility=visibility)
        if start:
            queryset = queryset.filter(created_at__date__gte=start)
        if end:
            queryset = queryset.filter(created_at__date__lte=end)

        paginator = Paginator(queryset.order_by("-updated_at"), 20)
        page = paginator.get_page(self.request.GET.get("page"))

        context.update(
            {
                "page_obj": page,
                "keyword": keyword,
                "visibility": visibility,
                "start": self.request.GET.get("start", ""),
                "end": self.request.GET.get("end", ""),
            }
        )
        return context


class WorkspaceDetailAdminView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/workspace_detail.html"

    def get_workspace(self):
        workspace = Novel.objects.filter(id=self.kwargs.get("workspace_id"), is_deleted=False).select_related("author").first()
        if not workspace:
            raise Http404("工作区不存在")
        return workspace

    def post(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        action = request.POST.get("action")

        if action == "force_private":
            workspace.visibility = Novel.Visibility.PRIVATE
            workspace.save(update_fields=["visibility", "updated_at"])
            messages.success(request, "已强制设为私密")
        elif action == "toggle_lock":
            workspace.is_locked = not workspace.is_locked
            workspace.save(update_fields=["is_locked", "updated_at"])
            messages.success(request, "锁定状态已更新")
        elif action == "clear_cache":
            messages.success(request, "缓存清理已触发")

        write_audit(request.user, f"admin.workspace.detail.{action}", "workspace", workspace.id, {"title": workspace.title})
        return redirect("adminpanel:workspace-detail", workspace_id=workspace.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace = self.get_workspace()
        context.update(
            {
                "workspace": workspace,
                "chapters": workspace.chapters.order_by("order", "id"),
                "privacy_banner": workspace.visibility == Novel.Visibility.PRIVATE,
            }
        )
        return context


class UserManageView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/users.html"

    def post(self, request, *args, **kwargs):
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        user_obj = get_object_or_404(User, id=user_id)

        if action == "ban":
            user_obj.is_active = False
            user_obj.save(update_fields=["is_active"])
            messages.success(request, f"用户 {user_obj.username} 已封禁")
        elif action == "unban":
            user_obj.is_active = True
            user_obj.save(update_fields=["is_active"])
            messages.success(request, f"用户 {user_obj.username} 已解封")
        elif action == "set_role":
            role = request.POST.get("role")
            if role in {User.Role.AUTHOR, User.Role.EDITOR, User.Role.ADMIN}:
                if user_obj.is_superuser and role != User.Role.ADMIN:
                    messages.error(request, "不能降级超级管理员角色")
                else:
                    user_obj.role = role
                    user_obj.is_staff = role == User.Role.ADMIN or user_obj.is_superuser
                    user_obj.save(update_fields=["role", "is_staff"])
                    messages.success(request, f"用户 {user_obj.username} 角色已更新")
        elif action == "set_level":
            level = int(request.POST.get("custom_level", "1"))
            level = max(1, min(3, level))
            user_obj.custom_level = level
            user_obj.save(update_fields=["custom_level"])
            messages.success(request, f"用户 {user_obj.username} 高级权限等级已调整为 Lv.{level}")

        write_audit(request.user, f"admin.user.{action}", "user", user_obj.id, {"username": user_obj.username})
        return redirect("adminpanel:users")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = User.objects.all().order_by("-date_joined")

        keyword = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        status = self.request.GET.get("status", "").strip()

        if keyword:
            query_filter = Q(username__icontains=keyword) | Q(email__icontains=keyword)
            if keyword.isdigit():
                query_filter = query_filter | Q(id=int(keyword))
            queryset = queryset.filter(query_filter)
        if role in {User.Role.AUTHOR, User.Role.EDITOR, User.Role.ADMIN}:
            queryset = queryset.filter(role=role)
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "banned":
            queryset = queryset.filter(is_active=False)

        paginator = Paginator(queryset, 20)
        context.update(
            {
                "page_obj": paginator.get_page(self.request.GET.get("page")),
                "keyword": keyword,
                "role": role,
                "status": status,
            }
        )
        return context


class UserDetailAdminView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/user_detail.html"

    def get_user_obj(self):
        return get_object_or_404(User, id=self.kwargs.get("user_id"))

    def post(self, request, *args, **kwargs):
        user_obj = self.get_user_obj()
        action = request.POST.get("action")

        if action == "reset_homepage":
            cfg = AuthorHomepageConfig.objects.filter(author=user_obj).first()
            if cfg:
                cfg.template_choice = AuthorHomepageConfig.TemplateChoice.MINIMAL
                cfg.header_image_url = ""
                cfg.avatar_url = ""
                cfg.custom_html = ""
                cfg.custom_css = ""
                cfg.use_custom_page = False
                cfg.sandbox_mode = "allow-scripts allow-same-origin"
                cfg.save()
                messages.success(request, "主页装修配置已重置")
            else:
                messages.info(request, "该用户暂无主页配置")

            write_audit(request.user, "admin.user.reset_homepage", "user", user_obj.id, {"username": user_obj.username})

        return redirect("adminpanel:user-detail", user_id=user_obj.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.get_user_obj()
        context.update(
            {
                "target_user": user_obj,
                "workspaces": Novel.objects.filter(author=user_obj, is_deleted=False).order_by("-updated_at"),
                "css_requests": CustomCSSRequest.objects.filter(applicant=user_obj).order_by("-created_at")[:20],
                "audit_logs": AuditLog.objects.filter(actor=user_obj).order_by("-created_at")[:30],
                "homepage_config": AuthorHomepageConfig.objects.filter(author=user_obj).first(),
            }
        )
        return context


class ReviewQueueView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/review_queue.html"

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "review_css":
            req_id = request.POST.get("request_id")
            decision = request.POST.get("decision")
            review_note = request.POST.get("review_note", "").strip()
            css_request = get_object_or_404(CustomCSSRequest, id=req_id)

            result = validate_advanced_css(css_request.css_snippet)
            if decision == CustomCSSRequest.Status.APPROVED and not result.is_valid:
                messages.error(request, "命中高危规则，不能通过")
                return redirect("adminpanel:reviews")

            css_request.blocked_reasons = result.blocked_reasons
            css_request.warning_reasons = result.warning_reasons
            css_request.mark_reviewed(request.user, decision, review_note)
            css_request.save(
                update_fields=[
                    "status",
                    "review_note",
                    "reviewed_by",
                    "reviewed_at",
                    "blocked_reasons",
                    "warning_reasons",
                    "updated_at",
                ]
            )

            if decision == CustomCSSRequest.Status.APPROVED:
                scope = AdvancedStyleGrant.Scope.NOVEL if css_request.novel_id else AdvancedStyleGrant.Scope.ACCOUNT
                grant, _ = AdvancedStyleGrant.objects.get_or_create(
                    user=css_request.applicant,
                    novel=css_request.novel if scope == AdvancedStyleGrant.Scope.NOVEL else None,
                    scope=scope,
                    defaults={"granted_by": request.user, "enabled": True},
                )
                if not grant.enabled:
                    grant.enabled = True
                    grant.granted_by = request.user
                    grant.save(update_fields=["enabled", "granted_by", "updated_at"])

            messages.success(request, "审核结果已更新")
            write_audit(request.user, "admin.review.css", "css_request", css_request.id, {"status": decision})

        elif action == "handle_report":
            report_id = request.POST.get("report_id")
            decision = request.POST.get("decision")
            note = request.POST.get("handle_note", "").strip()
            report = get_object_or_404(ContentReport, id=report_id)

            if decision == "ignore":
                report.status = ContentReport.Status.IGNORED
            else:
                report.status = ContentReport.Status.RESOLVED
            report.handle_note = note
            report.handled_by = request.user
            report.save(update_fields=["status", "handle_note", "handled_by", "updated_at"])

            if decision == "delete_and_notify":
                if report.target_type == ContentReport.TargetType.ROAST and report.chapter_id:
                    RoastMessage.objects.filter(chapter_id=report.chapter_id, status=RoastMessage.Status.REPORTED).update(
                        status=RoastMessage.Status.HIDDEN, updated_at=timezone.now()
                    )
                if report.workspace_id:
                    report.workspace.visibility = Novel.Visibility.PRIVATE
                    report.workspace.save(update_fields=["visibility", "updated_at"])

            messages.success(request, "举报处理完成")
            write_audit(request.user, "admin.review.report", "report", report.id, {"decision": decision})

        return redirect("adminpanel:reviews")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "pending_css_requests": CustomCSSRequest.objects.filter(status=CustomCSSRequest.Status.PENDING)
                .select_related("applicant", "novel")
                .order_by("created_at"),
                "pending_reports": ContentReport.objects.filter(status=ContentReport.Status.PENDING)
                .select_related("reporter", "workspace", "chapter")
                .order_by("created_at"),
            }
        )
        return context


class RoastModerationView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/roasts.html"

    def post(self, request, *args, **kwargs):
        roast_id = request.POST.get("roast_id")
        action = request.POST.get("action")
        roast = get_object_or_404(RoastMessage, id=roast_id)

        if action == "hide":
            roast.status = RoastMessage.Status.HIDDEN
            roast.save(update_fields=["status", "updated_at"])
            messages.success(request, "吐槽已屏蔽")
        elif action == "restore":
            roast.status = RoastMessage.Status.NORMAL
            roast.save(update_fields=["status", "updated_at"])
            messages.success(request, "吐槽已恢复")
        elif action == "delete":
            roast.is_deleted = True
            roast.save(update_fields=["is_deleted", "updated_at"])
            messages.success(request, "吐槽已删除")

        write_audit(request.user, f"admin.roast.{action}", "roast", roast.id)
        return redirect("adminpanel:roasts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = RoastMessage.objects.filter(is_deleted=False).select_related("workspace", "chapter", "author", "mentioned_user")

        visibility = self.request.GET.get("visibility", "")
        status = self.request.GET.get("status", "")
        keyword = self.request.GET.get("q", "").strip()

        if visibility in {RoastMessage.Visibility.INTERNAL, RoastMessage.Visibility.EDITOR, RoastMessage.Visibility.PRIVATE}:
            queryset = queryset.filter(visibility=visibility)
        if status in {RoastMessage.Status.NORMAL, RoastMessage.Status.REPORTED, RoastMessage.Status.HIDDEN}:
            queryset = queryset.filter(status=status)
        if keyword:
            queryset = queryset.filter(Q(content__icontains=keyword) | Q(workspace__title__icontains=keyword))

        selected_id = self.request.GET.get("id")
        selected_roast = queryset.filter(id=selected_id).first() if selected_id else None

        paginator = Paginator(queryset.order_by("-created_at"), 20)
        context.update(
            {
                "page_obj": paginator.get_page(self.request.GET.get("page")),
                "selected_roast": selected_roast,
                "visibility": visibility,
                "status": status,
                "keyword": keyword,
            }
        )
        return context


class SystemSettingsView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/settings.html"

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        setting = PlatformSetting.get_solo()

        if action == "save_platform_settings":
            registration_mode = request.POST.get("registration_mode", PlatformSetting.RegistrationMode.INVITE_ONLY)
            if registration_mode not in {PlatformSetting.RegistrationMode.OPEN, PlatformSetting.RegistrationMode.INVITE_ONLY}:
                registration_mode = PlatformSetting.RegistrationMode.INVITE_ONLY

            review_mode = request.POST.get("advanced_css_review_mode", PlatformSetting.CssReviewMode.MANUAL)
            if review_mode not in {PlatformSetting.CssReviewMode.MANUAL, PlatformSetting.CssReviewMode.AUTO}:
                review_mode = PlatformSetting.CssReviewMode.MANUAL

            setting.registration_mode = registration_mode
            setting.default_registration_role = request.POST.get("default_registration_role", "author")
            setting.advanced_css_review_mode = review_mode
            setting.sandbox_preset = request.POST.get("sandbox_preset", "allow-scripts allow-same-origin")
            setting.sensitive_words = request.POST.get("sensitive_words", "")
            setting.ip_whitelist = request.POST.get("ip_whitelist", "")
            setting.ip_blacklist = request.POST.get("ip_blacklist", "")
            setting.require_public_review = request.POST.get("require_public_review") == "on"
            setting.save()

            messages.success(request, "系统设置已保存")
            write_audit(request.user, "admin.settings.update", "platform_setting", setting.id)

        elif action == "generate_invites":
            prefix = request.POST.get("prefix", "INV").strip().upper() or "INV"
            count = int(request.POST.get("count", "10"))
            count = max(1, min(500, count))

            codes = []
            for _ in range(count):
                code = f"{prefix}-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                invite, created = InviteCode.objects.get_or_create(code=code)
                if created:
                    codes.append(invite.code)

            messages.success(request, f"邀请码生成完成，本次新增 {len(codes)} 条")
            write_audit(request.user, "admin.invite.generate", "invite_code", "batch", {"prefix": prefix, "count": len(codes)})

        elif action == "invalidate_invite":
            code_id = request.POST.get("code_id")
            code = get_object_or_404(InviteCode, id=code_id)
            code.is_active = False
            code.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"邀请码 {code.code} 已失效")
            write_audit(request.user, "admin.invite.invalidate", "invite_code", code.id)

        return redirect("adminpanel:settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setting = PlatformSetting.get_solo()
        invite_codes = InviteCode.objects.order_by("-created_at")[:80]
        invite_batches = (
            InviteCode.objects.values("is_active")
            .annotate(total=Count("id"), used=Count("id", filter=Q(used_by__isnull=False)))
            .order_by("-is_active")
        )
        context.update(
            {
                "platform_setting": setting,
                "invite_codes": invite_codes,
                "invite_batches": invite_batches,
            }
        )
        return context


class AnalyticsView(AdminRequiredMixin, TemplateView):
    template_name = "adminpanel/analytics.html"

    def get_range(self):
        preset = self.request.GET.get("preset", "week")
        today = timezone.localdate()

        if preset == "today":
            start = today
            end = today
        elif preset == "month":
            start = today - timedelta(days=29)
            end = today
        elif preset == "custom":
            start = parse_date(self.request.GET.get("start")) or (today - timedelta(days=6))
            end = parse_date(self.request.GET.get("end")) or today
        else:
            start = today - timedelta(days=6)
            end = today

        if end < start:
            start, end = end, start

        return preset, start, end

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        preset, start, end = self.get_range()
        start_dt = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
        end_dt = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

        users_series = User.objects.filter(date_joined__range=(start_dt, end_dt)).annotate(day=TruncDate("date_joined")).values("day").annotate(total=Count("id"))
        workspace_series = Novel.objects.filter(created_at__range=(start_dt, end_dt), is_deleted=False).annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id"))
        chapter_series = Chapter.objects.filter(created_at__range=(start_dt, end_dt)).annotate(day=TruncDate("created_at")).values("day").annotate(total=Count("id"))

        context.update(
            {
                "preset": preset,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "new_users": User.objects.filter(date_joined__range=(start_dt, end_dt)).count(),
                "active_authors": Novel.objects.filter(updated_at__range=(start_dt, end_dt), is_deleted=False).values("author").distinct().count(),
                "new_workspaces": Novel.objects.filter(created_at__range=(start_dt, end_dt), is_deleted=False).count(),
                "new_chapters": Chapter.objects.filter(created_at__range=(start_dt, end_dt)).count(),
                "published_chapters": Chapter.objects.filter(created_at__range=(start_dt, end_dt), is_published=True).count(),
                "roast_total": RoastMessage.objects.filter(created_at__range=(start_dt, end_dt)).count(),
                "report_total": ContentReport.objects.filter(created_at__range=(start_dt, end_dt)).count(),
                "users_series": list(users_series),
                "workspace_series": list(workspace_series),
                "chapter_series": list(chapter_series),
            }
        )
        return context


class OpsToolsView(SuperAdminRequiredMixin, TemplateView):
    template_name = "adminpanel/ops.html"

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "clear_cache":
            cache.clear()
            messages.success(request, "缓存已清理")
        elif action == "reindex":
            messages.success(request, "已触发重建索引任务（示意）")

        write_audit(request.user, f"admin.ops.{action}", "system", action)
        return redirect("adminpanel:ops")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "audit_logs": AuditLog.objects.select_related("actor").order_by("-created_at")[:500],
            }
        )
        return context
