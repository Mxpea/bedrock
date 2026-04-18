from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="novel",
            name="last_open_chapter_id",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="novel",
            name="last_open_module",
            field=models.CharField(
                choices=[
                    ("writing", "正文"),
                    ("outline", "大纲"),
                    ("characters", "人物"),
                    ("worldbuilding", "世界观"),
                    ("appearance", "外观定制"),
                    ("settings", "工作区设置"),
                ],
                default="writing",
                max_length=24,
            ),
        ),
    ]
