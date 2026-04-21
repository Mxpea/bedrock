from .base import *  # noqa
import os

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Local-first defaults: run without PostgreSQL/Redis.
if os.getenv("DEV_USE_SQLITE", "True") == "True":
	DATABASES = {
		"default": {
			"ENGINE": "django.db.backends.sqlite3",
			"NAME": BASE_DIR / "db.sqlite3",
		}
	}

# Execute Celery tasks in-process for local development.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
