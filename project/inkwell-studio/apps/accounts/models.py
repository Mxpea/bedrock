from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel
import hashlib
import secrets


class User(AbstractUser):
    class Role(models.TextChoices):
        AUTHOR = "author", "Author"
        EDITOR = "editor", "Editor"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AUTHOR)
    custom_level = models.PositiveSmallIntegerField(default=1)
    # Two-factor authentication (TOTP)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=128, null=True, blank=True)
    # JSON list of hashed one-time recovery codes (stored as sha256 hex digests)
    two_factor_recovery_codes = models.JSONField(default=list, blank=True)

    def generate_recovery_codes(self, count: int = 10) -> list:
        codes = []
        hashed = []
        for _ in range(count):
            code = secrets.token_urlsafe(8)
            codes.append(code)
            hashed.append(hashlib.sha256(code.encode()).hexdigest())
        self.two_factor_recovery_codes = hashed
        self.save(update_fields=["two_factor_recovery_codes"])
        return codes

    def verify_and_consume_recovery_code(self, code: str) -> bool:
        h = hashlib.sha256(code.encode()).hexdigest()
        if h in (self.two_factor_recovery_codes or []):
            lst = list(self.two_factor_recovery_codes)
            lst.remove(h)
            self.two_factor_recovery_codes = lst
            self.save(update_fields=["two_factor_recovery_codes"])
            return True
        return False

    REQUIRED_FIELDS = ["email"]

    def is_admin_user(self) -> bool:
        """Return True for superusers, staff, and users with the admin role."""
        return bool(self.is_superuser or self.is_staff or self.role == self.Role.ADMIN)


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
