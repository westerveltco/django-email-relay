from __future__ import annotations

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    EMAIL_RELAY_DATABASE_ALIAS: {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DATABASE_ROUTERS = [
    "email_relay.db.EmailDatabaseRouter",
]


EMAIL_BACKEND = "email_relay.backend.DatabaseEmailBackend"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "email_relay",
]

SECRET_KEY = "NOTASECRET"

USE_TZ = True
