from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0005_character"),
    ]

    operations = [
        migrations.AddField(
            model_name="novel",
            name="outline_canvas",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
