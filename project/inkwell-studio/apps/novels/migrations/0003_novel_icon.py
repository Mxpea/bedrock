from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("novels", "0002_workspace_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="novel",
            name="icon",
            field=models.ImageField(blank=True, null=True, upload_to="workspace_icons/"),
        ),
    ]
