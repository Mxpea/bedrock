import os

from .base import *  # noqa


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


DEBUG = False

# Enforce HTTPS in production.
# Prefer DJANGO_* env names, but keep plain names for compatibility.
SECURE_SSL_REDIRECT = _env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    _env_bool("SECURE_SSL_REDIRECT", True),
)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Warn loudly if the secret key has not been changed from a known placeholder value.
_PLACEHOLDER_KEYS = {"unsafe-dev-key", "change-me"}
if os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key") in _PLACEHOLDER_KEYS:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong random value in production!")
