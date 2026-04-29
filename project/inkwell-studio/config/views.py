from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.customization.markdown_extensions import sanitize_advanced_content, sanitize_standard_content
from apps.customization.models import AuthorHomepageConfig, ThemeConfig
from apps.novels.models import Chapter, Novel

User = get_user_model()


class HomePageView(TemplateView):
    template_name = "home.html"


class LoginPageView(TemplateView):
    template_name = "auth/login.html"


class RegisterPageView(TemplateView):
    template_name = "auth/register.html"


class DashboardPageView(TemplateView):
    template_name = "dashboard/index.html"


class AccountSettingsPageView(LoginRequiredMixin, TemplateView):
    template_name = "account/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"user_obj": self.request.user})
        return context


class NovelListPageView(TemplateView):
    template_name = "novels/list.html"


class WorkspacePageView(LoginRequiredMixin, TemplateView):
    template_name = "workspace/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_id = kwargs.get("workspace_id")
        module = kwargs.get("module") or Novel.Module.WRITING

        workspace_filter = models.Q(public_id=workspace_id)
        if str(workspace_id).isdigit():
            workspace_filter |= models.Q(id=workspace_id)

        workspace = get_object_or_404(Novel, workspace_filter, is_deleted=False)
        if workspace.author != self.request.user:
            raise Http404("你无权访问该工作区")

        if module not in {choice[0] for choice in Novel.Module.choices}:
            module = Novel.Module.WRITING

        chapters = workspace.chapters.order_by("order", "id")
        chapter_id = self.request.GET.get("chapter_id") or workspace.last_open_chapter_id
        active_chapter = chapters.filter(id=chapter_id).first() if chapter_id else chapters.first()

        workspace.last_open_module = module
        update_fields = ["last_open_module", "updated_at"]
        if active_chapter:
            workspace.last_open_chapter_id = active_chapter.id
            update_fields.insert(1, "last_open_chapter_id")
        workspace.save(update_fields=update_fields)

        context.update(
            {
                "workspace": workspace,
                "module": module,
                "chapters": chapters,
                "active_chapter": active_chapter,
                "module_labels": dict(Novel.Module.choices),
                "module_label": dict(Novel.Module.choices).get(module, module),
            }
        )

        if module == Novel.Module.APPEARANCE:
            context.update(
                {
                    "theme_config": ThemeConfig.objects.filter(novel=workspace).first(),
                    "theme_font_choices": ThemeConfig.SAFE_FONT_CHOICES,
                }
            )

        if module == Novel.Module.OUTLINE:
            context.update(
                {
                    "outline_canvas": workspace.outline_canvas or {},
                }
            )

        if module == Novel.Module.WORLDBUILDING:
            context.update(
                {
                    "worldbuilding_data": workspace.worldbuilding_data or {},
                    "world_chapter_refs": list(
                        chapters.values("id", "title", "order")
                    ),
                    "world_character_refs": list(
                        workspace.characters.order_by("name", "id").values("id", "name")
                    ),
                }
            )

        return context


class ReaderPageView(TemplateView):
    template_name = "novels/reader.html"

    def _accessible_chapters(self):
        user = self.request.user
        base_qs = Chapter.objects.select_related("novel", "novel__author").filter(novel__is_deleted=False)

        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return base_qs

        if user.is_authenticated:
            return base_qs.filter(
                models.Q(novel__author=user)
                | models.Q(novel__visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK])
            )

        return base_qs.filter(
            novel__visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chapter_qs = self._accessible_chapters()

        chapter_id = kwargs.get("chapter_id") or self.request.GET.get("chapter_id")
        workspace_id = self.request.GET.get("workspace_id") or self.request.GET.get("novel_id")

        chapter = None
        if chapter_id:
            chapter = chapter_qs.filter(id=chapter_id).first()
        elif workspace_id:
            chapter_filter = models.Q(novel__public_id=workspace_id)
            if str(workspace_id).isdigit():
                chapter_filter |= models.Q(novel_id=workspace_id)
            chapter = chapter_qs.filter(chapter_filter).order_by("order", "id").first()
        else:
            chapter = chapter_qs.order_by("-updated_at").first()

        if not chapter:
            context.update(
                {
                    "chapter": None,
                    "chapter_list": [],
                    "prev_chapter_id": None,
                    "next_chapter_id": None,
                }
            )
            return context

        chapter_list_qs = chapter_qs.filter(novel=chapter.novel).order_by("order", "id")
        chapter_ids = list(chapter_list_qs.values_list("id", flat=True))
        current_idx = chapter_ids.index(chapter.id)

        prev_chapter_id = chapter_ids[current_idx - 1] if current_idx > 0 else None
        next_chapter_id = chapter_ids[current_idx + 1] if current_idx < len(chapter_ids) - 1 else None

        context.update(
            {
                "chapter": chapter,
                "chapter_rendered_html": (
                    sanitize_advanced_content(chapter.content_md)
                    if chapter._author_has_advanced_markdown_access()
                    else sanitize_standard_content(chapter.content_md)
                ),
                "chapter_list": chapter_list_qs,
                "prev_chapter_id": prev_chapter_id,
                "next_chapter_id": next_chapter_id,
                "reader_theme": ThemeConfig.objects.filter(novel=chapter.novel).first(),
            }
        )
        return context


class AuthorProfilePageView(TemplateView):
    template_name = "author_profile.html"

    def _default_schema(self):
        return {
            "modules": [
                {
                    "id": "works-default",
                    "type": "works",
                    "title": "作品陈列柜",
                    "style": "grid",
                    "sort": "updated",
                    "limit": 6,
                },
                {
                    "id": "bio-default",
                    "type": "bio",
                    "title": "作者简介",
                    "content": "",
                },
                {
                    "id": "timeline-default",
                    "type": "timeline",
                    "title": "创作时间轴",
                    "show_chapter_name": True,
                    "limit": 8,
                },
            ]
        }

    def _serialize_workspaces(self, queryset):
        items = []
        for workspace in queryset:
            items.append(
                {
                    "id": workspace.public_id,
                    "title": workspace.title,
                    "summary": workspace.summary or "",
                    "cover_url": workspace.icon.url if workspace.icon else "",
                    "visibility": workspace.visibility,
                    "visibility_label": workspace.get_visibility_display(),
                    "updated_at": workspace.updated_at.isoformat() if workspace.updated_at else "",
                    "public_id": workspace.public_id,
                    "chapter_count": workspace.chapters.filter(is_published=True).count(),
                    "read_url": f"/reader/?workspace_id={workspace.public_id}",
                }
            )
        return items

    def _serialize_timeline(self, chapter_queryset):
        result = []
        for chapter in chapter_queryset:
            result.append(
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "workspace_title": chapter.novel.title,
                    "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else "",
                    "url": f"/reader/{chapter.id}/",
                }
            )
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = kwargs.get("username")
        profile_user = get_object_or_404(User, username=username)
        is_owner = self.request.user.is_authenticated and self.request.user == profile_user
        decorate_mode = is_owner and self.request.GET.get("decorate") == "1"

        base_workspaces = Novel.objects.filter(author=profile_user, is_deleted=False)
        public_workspaces = base_workspaces.filter(visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK])

        if is_owner:
            workspaces = base_workspaces.order_by("-updated_at")
        else:
            workspaces = public_workspaces.order_by("-updated_at")

        public_workspaces_count = public_workspaces.count()
        public_chapters_count = Chapter.objects.filter(novel__in=public_workspaces, is_published=True).count()
        days_joined = (timezone.now() - profile_user.date_joined).days
        timeline_qs = Chapter.objects.filter(novel__in=public_workspaces, is_published=True).select_related("novel").order_by("-updated_at")[:20]

        homepage_config, _ = AuthorHomepageConfig.objects.get_or_create(author=profile_user)
        default_schema = self._default_schema()
        published_schema = homepage_config.page_schema_published or default_schema
        draft_schema = homepage_config.page_schema_draft or published_schema
        active_schema = draft_schema if decorate_mode else published_schema

        context.update({
            "profile_user": profile_user,
            "is_owner": is_owner,
            "decorate_mode": decorate_mode,
            "workspaces": workspaces,
            "public_workspaces_count": public_workspaces_count,
            "public_chapters_count": public_chapters_count,
            "days_joined": days_joined,
            "homepage_config": homepage_config,
            "homepage_schema": active_schema,
            "homepage_schema_published": published_schema,
            "homepage_schema_draft": draft_schema,
            "homepage_modules_payload": self._serialize_workspaces(public_workspaces.order_by("-updated_at")),
            "homepage_timeline_payload": self._serialize_timeline(timeline_qs),
        })
        return context


class NovelDetailPageView(TemplateView):
    template_name = "novels/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workspace_id = kwargs.get("novel_id")
        
        # Check permissions similar to reader
        user = self.request.user
        base_qs = Novel.objects.filter(is_deleted=False)
        
        novel_filter = models.Q(public_id=workspace_id)
        if str(workspace_id).isdigit():
            novel_filter |= models.Q(id=workspace_id)
            
        novel = get_object_or_404(base_qs, novel_filter)
        
        # Ensure user can see this novel
        if not (user.is_authenticated and (user.is_staff or user.is_superuser or novel.author == user)):
            if novel.visibility not in [Novel.Visibility.PUBLIC, Novel.Visibility.LINK]:
                raise Http404("无权访问该工作区")
                
        context["novel"] = novel
        
        # Get accessible chapters
        chap_base = novel.chapters.all()
        if not (user.is_authenticated and (user.is_staff or user.is_superuser or novel.author == user)):
            chap_base = chap_base.filter(is_published=True)
            
        context["chapter_list"] = chap_base.order_by("order", "id")
        return context
