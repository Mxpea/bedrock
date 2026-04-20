from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0008_worldviewentry_worldviewlink"),
    ]

    operations = [
        migrations.AddField(
            model_name="worldviewentry",
            name="folder_path",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
        ),
    ]
