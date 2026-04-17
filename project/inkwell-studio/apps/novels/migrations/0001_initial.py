from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Novel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("summary", models.TextField(blank=True)),
                (
                    "visibility",
                    models.CharField(
                        choices=[("private", "私密"), ("link", "链接可见"), ("public", "公开")],
                        default="private",
                        max_length=16,
                    ),
                ),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "author",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="novels", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Chapter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("content_md", models.TextField(default="")),
                ("content_html", models.TextField(blank=True, default="")),
                ("order", models.PositiveIntegerField(default=1)),
                ("is_published", models.BooleanField(default=False)),
                (
                    "novel",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="chapters", to="novels.novel"),
                ),
            ],
            options={"ordering": ["order", "id"], "unique_together": {("novel", "order")}},
        ),
    ]
