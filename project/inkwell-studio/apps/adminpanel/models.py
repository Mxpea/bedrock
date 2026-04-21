from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class PlatformSetting(TimeStampedModel):
    class RegistrationMode(models.TextChoices):
        OPEN = "open", "开放注册"
        INVITE_ONLY = "invite_only", "仅邀请码注册"

    class CssReviewMode(models.TextChoices):
        MANUAL = "manual", "手动审核"
        AUTO = "auto", "自动通过（高风险）"

    registration_mode = models.CharField(max_length=24, choices=RegistrationMode.choices, default=RegistrationMode.INVITE_ONLY)
    default_registration_role = models.CharField(max_length=16, default="author")
    advanced_css_review_mode = models.CharField(max_length=16, choices=CssReviewMode.choices, default=CssReviewMode.MANUAL)
    sandbox_preset = models.CharField(max_length=128, default="allow-scripts allow-same-origin")
    sensitive_words = models.TextField(blank=True)
    ip_whitelist = models.TextField(blank=True)
    ip_blacklist = models.TextField(blank=True)
    require_public_review = models.BooleanField(default=False)

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class ContentReport(TimeStampedModel):
    class TargetType(models.TextChoices):
        WORKSPACE = "workspace", "作品内容"
        HOMEPAGE = "homepage", "主页装修"
        ROAST = "roast", "吐槽"
        OTHER = "other", "其他"

    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        IGNORED = "ignored", "已忽略"
        RESOLVED = "resolved", "已处理"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    target_type = models.CharField(max_length=24, choices=TargetType.choices, default=TargetType.WORKSPACE)
    workspace = models.ForeignKey("novels.Novel", on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey("novels.Chapter", on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_reports",
    )
    handle_note = models.TextField(blank=True)


class RoastMessage(TimeStampedModel):
    class Visibility(models.TextChoices):
        INTERNAL = "internal", "内部公开"
        EDITOR = "editor", "编辑组"
        PRIVATE = "private", "私密"

    class Status(models.TextChoices):
        NORMAL = "normal", "正常"
        REPORTED = "reported", "被举报"
        HIDDEN = "hidden", "已屏蔽"

    workspace = models.ForeignKey("novels.Novel", on_delete=models.CASCADE, related_name="roast_messages")
    chapter = models.ForeignKey("novels.Chapter", on_delete=models.SET_NULL, null=True, blank=True, related_name="roast_messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="roast_messages")
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentioned_in_roasts",
    )
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.INTERNAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NORMAL)
    content = models.TextField()
    is_deleted = models.BooleanField(default=False)


class RoastReply(TimeStampedModel):
    roast = models.ForeignKey(RoastMessage, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    is_deleted = models.BooleanField(default=False)
