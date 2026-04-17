import bleach
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Novel(TimeStampedModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "私密"
        LINK = "link", "链接可见"
        PUBLIC = "public", "公开"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="novels")
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
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

    def save(self, *args, **kwargs):
        # Keep rendered HTML sanitized to reduce stored-XSS risk.
        self.content_html = bleach.clean(self.content_md, tags=[], attributes={}, strip=True).replace("\n", "<br>")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.novel.title}-{self.title}"
