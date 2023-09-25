from __future__ import annotations

import logging

from django.conf import settings

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS

pytest_plugins = []  # type: ignore


# Settings fixtures to bootstrap our tests
def pytest_configure(config):
    logging.disable(logging.CRITICAL)

    settings.configure(
        ALLOWED_HOSTS=["*"],
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        },
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
            EMAIL_RELAY_DATABASE_ALIAS: {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            },
        },
        DATABASE_ROUTERS=[
            "email_relay.db.EmailDatabaseRouter",
        ],
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "email_relay",
        ],
        LOGGING_CONFIG=None,
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
        SECRET_KEY="NOTASECRET",
        USE_TZ=True,
    )
