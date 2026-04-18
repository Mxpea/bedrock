from django.conf import settings
from django.db import models

from apps.customization.markdown_extensions import sanitize_advanced_content, sanitize_standard_content
from apps.customization.models import AdvancedStyleGrant
from apps.core.models import TimeStampedModel


class Novel(TimeStampedModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "私密"
        LINK = "link", "链接可见"
        PUBLIC = "public", "公开"

    class Module(models.TextChoices):
        WRITING = "writing", "正文"
        OUTLINE = "outline", "大纲"
        CHARACTERS = "characters", "人物"
        WORLDBUILDING = "worldbuilding", "世界观"
        APPEARANCE = "appearance", "外观定制"
        SETTINGS = "settings", "工作区设置"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="novels")
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    icon = models.ImageField(upload_to="workspace_icons/", blank=True, null=True)
    is_locked = models.BooleanField(default=False)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE)
    last_open_module = models.CharField(max_length=24, choices=Module.choices, default=Module.WRITING)
    last_open_chapter_id = models.PositiveIntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def workspace_name(self) -> str:
        return self.title


class Chapter(TimeStampedModel):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200)
    content_md = models.TextField(default="")
    content_html = models.TextField(default="", blank=True)
    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("novel", "order")

    def _author_has_advanced_markdown_access(self) -> bool:
        author = self.novel.author
        return AdvancedStyleGrant.objects.filter(
            user=author,
            enabled=True,
            scope=AdvancedStyleGrant.Scope.ACCOUNT,
        ).exists() or AdvancedStyleGrant.objects.filter(
            user=author,
            novel=self.novel,
            enabled=True,
            scope=AdvancedStyleGrant.Scope.NOVEL,
        ).exists()

    def save(self, *args, **kwargs):
        # Standard authors use strict token rendering; advanced authors get limited HTML tags.
        if self._author_has_advanced_markdown_access():
            self.content_html = sanitize_advanced_content(self.content_md)
        else:
            self.content_html = sanitize_standard_content(self.content_md)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.novel.title}-{self.title}"
