from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_managers_user_custom_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="two_factor_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="two_factor_secret",
            field=models.CharField(max_length=128, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="two_factor_recovery_codes",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
