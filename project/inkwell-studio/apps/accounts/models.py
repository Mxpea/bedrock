from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    class Role(models.TextChoices):
        AUTHOR = "author", "Author"
        EDITOR = "editor", "Editor"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AUTHOR)
    custom_level = models.PositiveSmallIntegerField(default=1)

    REQUIRED_FIELDS = ["email"]


class InviteCode(TimeStampedModel):
    code = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.code


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=128)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.action}#{self.pk}"
