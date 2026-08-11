from __future__ import annotations

import logging
import os

from django.conf import settings

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS

from .settings import DEFAULT_SETTINGS

pytest_plugins = []  # type: ignore


def pytest_configure(config):
    logging.disable(logging.CRITICAL)

    DEFAULT_SETTINGS.pop("DATABASES", None)

    settings.configure(
        **DEFAULT_SETTINGS,
        **TEST_SETTINGS,
    )


def database_settings(name: str) -> dict[str, object]:
    if host := os.getenv("POSTGRES_HOST"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": host,
            "NAME": name,
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


TEST_SETTINGS = {
    "DATABASES": {
        "default": database_settings("defaultdb"),
        EMAIL_RELAY_DATABASE_ALIAS: database_settings("relaydb"),
    },
    "DATABASE_ROUTERS": [
        "email_relay.db.EmailDatabaseRouter",
    ],
    "INSTALLED_APPS": [
        "django.contrib.contenttypes",
        "email_relay",
    ],
}
