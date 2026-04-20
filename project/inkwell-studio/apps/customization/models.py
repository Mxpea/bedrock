from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ThemeConfig(TimeStampedModel):
    class BackgroundMode(models.TextChoices):
        SCROLL_TILE = "scroll_tile", "随页面滚动并平铺"
        FIXED_COVER = "fixed_cover", "静止背景"

    SAFE_FONT_CHOICES = [
        ("Noto Serif SC", "Noto Serif SC"),
        ("Noto Sans SC", "Noto Sans SC"),
        ("Source Han Serif SC", "Source Han Serif SC"),
        ("Source Han Sans SC", "Source Han Sans SC"),
        ("FangSong", "FangSong"),
        ("KaiTi", "KaiTi"),
        ("SimSun", "SimSun"),
        ("Microsoft YaHei", "Microsoft YaHei"),
        ("PingFang SC", "PingFang SC"),
        ("Segoe UI", "Segoe UI"),
    ]

    novel = models.OneToOneField("novels.Novel", on_delete=models.CASCADE, related_name="theme_config")
    page_bg_color = models.CharField(max_length=32, default="#fffaf2")
    background_image = models.ImageField(upload_to="theme_backgrounds/", blank=True, null=True)
    background_mode = models.CharField(
        max_length=20,
        choices=BackgroundMode.choices,
        default=BackgroundMode.SCROLL_TILE,
    )
    background_opacity = models.FloatField(default=0.22)
    text_font_family = models.CharField(max_length=64, choices=SAFE_FONT_CHOICES, default="Noto Serif SC")
    link_color = models.CharField(max_length=32, default="#16324f")
    paragraph_spacing = models.CharField(max_length=16, default="1rem")


class AdvancedStyleGrant(TimeStampedModel):
    class Scope(models.TextChoices):
        ACCOUNT = "account", "Account"
        NOVEL = "novel", "Novel"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="advanced_style_grants")
    novel = models.ForeignKey("novels.Novel", on_delete=models.CASCADE, null=True, blank=True)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.ACCOUNT)
    enabled = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_advanced_styles",
    )

    class Meta:
        unique_together = ("user", "novel", "scope")


class CustomCSSRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="css_requests")
    novel = models.ForeignKey("novels.Novel", on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField()
    css_snippet = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_css_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    risk_acknowledged = models.BooleanField(default=False)
    blocked_reasons = models.JSONField(default=list, blank=True)
    warning_reasons = models.JSONField(default=list, blank=True)

    def mark_reviewed(self, reviewer, status: str, note: str = "") -> None:
        self.status = status
        self.review_note = note
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()


class CSSSecurityEvent(TimeStampedModel):
    class Severity(models.TextChoices):
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    novel = models.ForeignKey("novels.Novel", on_delete=models.CASCADE, related_name="css_events")
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices)
    reason = models.CharField(max_length=255)
    matched_css_fragment = models.TextField(blank=True)
    auto_rollback_applied = models.BooleanField(default=False)


class AuthorHomepageConfig(TimeStampedModel):
    class TemplateChoice(models.TextChoices):
        MINIMAL = "minimal", "Minimal"
        MAGAZINE = "magazine", "Magazine"
        TIMELINE = "timeline", "Timeline"
        PORTFOLIO = "portfolio", "Portfolio"
        NOTEBOOK = "notebook", "Notebook"
        CINEMATIC = "cinematic", "Cinematic"

    author = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="homepage_config")
    template_choice = models.CharField(max_length=24, choices=TemplateChoice.choices, default=TemplateChoice.MINIMAL)
    header_image_url = models.URLField(blank=True)
    header_image = models.ImageField(upload_to='author_headers/', blank=True, null=True)
    avatar_url = models.URLField(blank=True)
    avatar = models.ImageField(upload_to='author_avatars/', blank=True, null=True)
    author_bio = models.TextField(blank=True, default="")
    custom_html = models.TextField(blank=True)
    custom_css = models.TextField(blank=True)
    use_custom_page = models.BooleanField(default=False)
    sandbox_mode = models.CharField(max_length=64, default="allow-scripts allow-same-origin")
    page_schema_draft = models.JSONField(default=dict, blank=True)
    page_schema_published = models.JSONField(default=dict, blank=True)
    global_style = models.JSONField(default=dict, blank=True)


class CustomFont(TimeStampedModel):
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploaded_fonts")
    name = models.CharField(max_length=64)
    font_file = models.FileField(upload_to="fonts/")
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.uploader.username})"
