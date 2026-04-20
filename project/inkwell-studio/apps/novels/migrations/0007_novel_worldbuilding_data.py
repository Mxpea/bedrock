from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0006_novel_outline_canvas"),
    ]

    operations = [
        migrations.AddField(
            model_name="novel",
            name="worldbuilding_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
