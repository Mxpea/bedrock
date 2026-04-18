from django.views.generic import TemplateView
from django.db import models
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

class HomePageView(TemplateView):
    template_name = "home.html"


class LoginPageView(TemplateView):
    template_name = "auth/login.html"


class RegisterPageView(TemplateView):
    template_name = "auth/register.html"


class DashboardPageView(TemplateView):
    template_name = "dashboard/index.html"


class NovelListPageView(TemplateView):
    template_name = "novels/list.html"

class EditorPageView(TemplateView):
    template_name = "novels/editor.html"

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
                | models.Q(novel__visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK], is_published=True)
            )

        return base_qs.filter(
            novel__visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK],
            is_published=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chapter_qs = self._accessible_chapters()

        chapter_id = kwargs.get("chapter_id") or self.request.GET.get("chapter_id")
        novel_id = self.request.GET.get("novel_id")

        chapter = None
        if chapter_id:
            chapter = chapter_qs.filter(id=chapter_id).first()
        elif novel_id:
            chapter = chapter_qs.filter(novel_id=novel_id).order_by("order", "id").first()
        else:
            chapter = chapter_qs.order_by("-updated_at").first()

        if not chapter:
            context.update({
                "chapter": None,
                "chapter_list": [],
                "prev_chapter_id": None,
                "next_chapter_id": None,
            })
            return context

        chapter_list_qs = chapter_qs.filter(novel=chapter.novel).order_by("order", "id")
        chapter_ids = list(chapter_list_qs.values_list("id", flat=True))
        current_idx = chapter_ids.index(chapter.id)

        prev_chapter_id = chapter_ids[current_idx - 1] if current_idx > 0 else None
        next_chapter_id = chapter_ids[current_idx + 1] if current_idx < len(chapter_ids) - 1 else None

        context.update({
            "chapter": chapter,
            "chapter_list": chapter_list_qs,
            "prev_chapter_id": prev_chapter_id,
            "next_chapter_id": next_chapter_id,
        })
        return context

class AuthorProfilePageView(TemplateView):
    template_name = "author_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = kwargs.get("username")
        profile_user = get_object_or_404(User, username=username)
        is_owner = self.request.user.is_authenticated and self.request.user == profile_user
        
        from apps.novels.models import Novel
        if is_owner:
            novels = Novel.objects.filter(author=profile_user, is_deleted=False).order_by("-updated_at")
        else:
            novels = Novel.objects.filter(author=profile_user, is_deleted=False, visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK]).order_by("-updated_at")

        context["profile_user"] = profile_user
        context["is_owner"] = is_owner
        context["novels"] = novels
        return context
