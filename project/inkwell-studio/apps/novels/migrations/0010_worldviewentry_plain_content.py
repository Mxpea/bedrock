from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0009_worldviewentry_folder_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="worldviewentry",
            name="plain_content",
            field=models.TextField(blank=True, default=""),
        ),
    ]
