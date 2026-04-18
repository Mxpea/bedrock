from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("novels", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthorHomepageConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "template_choice",
                    models.CharField(
                        choices=[
                            ("minimal", "Minimal"),
                            ("magazine", "Magazine"),
                            ("timeline", "Timeline"),
                            ("portfolio", "Portfolio"),
                            ("notebook", "Notebook"),
                            ("cinematic", "Cinematic"),
                        ],
                        default="minimal",
                        max_length=24,
                    ),
                ),
                ("header_image_url", models.URLField(blank=True)),
                ("avatar_url", models.URLField(blank=True)),
                ("custom_html", models.TextField(blank=True)),
                ("custom_css", models.TextField(blank=True)),
                ("use_custom_page", models.BooleanField(default=False)),
                ("sandbox_mode", models.CharField(default="allow-scripts allow-same-origin", max_length=64)),
                (
                    "author",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="homepage_config", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AdvancedStyleGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "scope",
                    models.CharField(choices=[("account", "Account"), ("novel", "Novel")], default="account", max_length=16),
                ),
                ("enabled", models.BooleanField(default=True)),
                (
                    "granted_by",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="granted_advanced_styles", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "novel",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to="novels.novel"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="advanced_style_grants", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CustomCSSRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reason", models.TextField()),
                ("css_snippet", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("review_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("risk_acknowledged", models.BooleanField(default=False)),
                ("blocked_reasons", models.JSONField(blank=True, default=list)),
                ("warning_reasons", models.JSONField(blank=True, default=list)),
                (
                    "applicant",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="css_requests", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "novel",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to="novels.novel"),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="reviewed_css_requests", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ThemeConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("page_bg_color", models.CharField(default="#fffaf2", max_length=32)),
                (
                    "text_font_family",
                    models.CharField(
                        choices=[
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
                        ],
                        default="Noto Serif SC",
                        max_length=64,
                    ),
                ),
                ("link_color", models.CharField(default="#16324f", max_length=32)),
                ("paragraph_spacing", models.CharField(default="1rem", max_length=16)),
                (
                    "novel",
                    models.OneToOneField(on_delete=models.deletion.CASCADE, related_name="theme_config", to="novels.novel"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CSSSecurityEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("severity", models.CharField(choices=[("warning", "Warning"), ("critical", "Critical")], max_length=16)),
                ("reason", models.CharField(max_length=255)),
                ("matched_css_fragment", models.TextField(blank=True)),
                ("auto_rollback_applied", models.BooleanField(default=False)),
                (
                    "novel",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="css_events", to="novels.novel"),
                ),
                (
                    "triggered_by",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="advancedstylegrant",
            unique_together={("user", "novel", "scope")},
        ),
    ]
