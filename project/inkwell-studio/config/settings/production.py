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
# Already set to False lower down to support HTTP deployment without .env
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Warn loudly if the secret key has not been changed from a known placeholder value.
_PLACEHOLDER_KEYS = {"unsafe-dev-key", "change-me"}
if os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key") in _PLACEHOLDER_KEYS:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a strong random value in production!")
# CSRF trusted origins – allow form submissions from specific domains / IPs
_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    # CSRF trusted origins – allow form submissions from specific domains / IPs
    _csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    # 确保 CSRF_TRUSTED_ORIGINS 存在
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(",") if origin.strip()]    
else:
    CSRF_TRUSTED_ORIGINS = []

# If not using HTTPS in your internal docker setup, this must be False or the browser will drop the CSRF cookie over HTTP.
# We default it to False here to prevent immediate 403s on non-HTTPS deployments.
_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in _csrf_origins.split(",") if origin.strip()])

# If no explicit CSRF_TRUSTED_ORIGINS were provided, derive sensible defaults
# from ALLOWED_HOSTS so deployed hosts like 47.105.123.24:50000 will be
# automatically trusted without editing files on every deploy. We add both
# http and https variants and include an optional port coming from env.
if not CSRF_TRUSTED_ORIGINS:
    ports = set()
    env_port = os.getenv("PORT") or os.getenv("DJANGO_PORT") or os.getenv("EXTERNAL_PORT")
    if env_port:
        ports.add(env_port.strip())
    # common HTTP port for deployments behind a reverse proxy
    ports.update(["80", "8000", "50000"]) 

    for h in ALLOWED_HOSTS:
        host = (h or "").strip()
        if not host:
            continue
        # add plain host (no port) variants
        CSRF_TRUSTED_ORIGINS.append(f"http://{host}")
        CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
        # add ported variants
        for p in ports:
            CSRF_TRUSTED_ORIGINS.append(f"http://{host}:{p}")
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}:{p}")

    # ensure uniqueness and strip
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([o.strip() for o in CSRF_TRUSTED_ORIGINS if o and o.strip()]))

# If not using HTTPS in your internal docker setup, CSRF cookie must be
# allowed over HTTP. Default to False here so non-HTTPS deployments do not
# immediately lose the CSRF cookie (set True when serving HTTPS).
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", False)
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)

# Do not force SSL redirect by default in containerized internal deploys;
# allow overriding via env vars when terminating TLS at the proxy.
SECURE_SSL_REDIRECT = _env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    _env_bool("SECURE_SSL_REDIRECT", False),
)
