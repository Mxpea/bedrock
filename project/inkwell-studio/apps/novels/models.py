from django.conf import settings
from django.db import models
import re

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
    outline_canvas = models.JSONField(default=dict, blank=True)
    worldbuilding_data = models.JSONField(default=dict, blank=True)
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
        # Only re-render content_html when content_md has actually changed.
        # This avoids an expensive Markdown render + AdvancedStyleGrant query
        # on every save (e.g. publishing, reordering).
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "content_md" in update_fields:
            if self._author_has_advanced_markdown_access():
                self.content_html = sanitize_advanced_content(self.content_md)
            else:
                self.content_html = sanitize_standard_content(self.content_md)
            if update_fields is not None and "content_html" not in update_fields:
                kwargs["update_fields"] = list(update_fields) + ["content_html"]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.novel.title}-{self.title}"


class Character(TimeStampedModel):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="characters")
    name = models.CharField(max_length=120)
    aliases = models.JSONField(default=list, blank=True)
    avatar = models.ImageField(upload_to="character_avatars/", blank=True, null=True)
    role_title = models.CharField(max_length=120, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    age_label = models.CharField(max_length=40, blank=True)
    tags = models.JSONField(default=list, blank=True)
    summary = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    relationships = models.JSONField(default=list, blank=True)
    chapter_mentions = models.JSONField(default=list, blank=True)
    is_starred = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-is_pinned", "sort_order", "id"]
        unique_together = ("novel", "name")

    def __str__(self) -> str:
        return f"{self.novel.title}-{self.name}"

    def compute_chapter_mentions(self):
        token_pat = re.compile(r"\{\s*@?人物\s*:\s*([^}]+?)\s*\}")
        at_pat = re.compile(r"(?<![\w\u4e00-\u9fa5])@([\u4e00-\u9fa5A-Za-z0-9_\-]{2,40})")

        names = {self.name.strip()}
        names.update([str(alias).strip() for alias in (self.aliases or []) if str(alias).strip()])

        hits = []
        for chapter in self.novel.chapters.all().order_by("order", "id"):
            text = chapter.content_md or ""
            matched = False

            for token_name in token_pat.findall(text):
                if token_name.strip() in names:
                    matched = True
                    break

            if not matched:
                for at_name in at_pat.findall(text):
                    if at_name.strip() in names:
                        matched = True
                        break

            if matched:
                hits.append(
                    {
                        "chapter_id": chapter.id,
                        "chapter_title": chapter.title,
                        "chapter_order": chapter.order,
                    }
                )

        return hits

class WorldviewEntry(TimeStampedModel):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="worldview_entries")
    name = models.CharField(max_length=120)
    aliases = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=50, blank=True, db_index=True)
    properties = models.JSONField(default=dict, blank=True)
    content_md = models.TextField(blank=True)
    content_html = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("novel", "name")

    def __str__(self) -> str:
        return f"{self.novel.title} - [Worldview] {self.name}"

class WorldviewLink(TimeStampedModel):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="worldview_links")
    source = models.ForeignKey(WorldviewEntry, on_delete=models.CASCADE, related_name="outgoing_links")
    target = models.ForeignKey(WorldviewEntry, on_delete=models.CASCADE, related_name="incoming_links")
    context = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("source", "target")

    def __str__(self) -> str:
        return f"{self.source.name} -> {self.target.name}"
