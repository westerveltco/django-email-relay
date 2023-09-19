from __future__ import annotations

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "email_relay.backend.DatabaseEmailBackend"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "email_relay",
    "tests",
]

SECRET_KEY = "NOTASECRET"

USE_TZ = True
