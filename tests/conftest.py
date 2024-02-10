from __future__ import annotations

import logging

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


TEST_SETTINGS = {
    "DATABASES": {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
        EMAIL_RELAY_DATABASE_ALIAS: {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    },
    "DATABASE_ROUTERS": [
        "email_relay.db.EmailDatabaseRouter",
    ],
    "INSTALLED_APPS": [
        "django.contrib.contenttypes",
        "email_relay",
    ],
}
