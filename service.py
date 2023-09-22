from __future__ import annotations

import os

import dj_database_url
import django
from django.conf import global_settings
from django.conf import settings
from django.core.management import call_command

DEBUG = os.getenv("EMAIL_RELAY_DEBUG", False)

SETTINGS = {
    "DATABASES": {
        "default": dj_database_url.parse(
            os.getenv("DATABASE_URL", ""),
            conn_max_age=600,  # 10 minutes
            conn_health_checks=True,
        ),
    },
    "DEBUG": DEBUG,
    "DEFAULT_FROM_EMAIL": os.getenv(
        "DEFAULT_FROM_EMAIL", global_settings.DEFAULT_FROM_EMAIL
    ),
    "EMAIL_HOST": os.getenv("EMAIL_HOST", global_settings.EMAIL_HOST),
    "EMAIL_HOST_PASSWORD": os.getenv(
        "EMAIL_HOST_PASSWORD", global_settings.EMAIL_HOST_PASSWORD
    ),
    "EMAIL_HOST_USER": os.getenv("EMAIL_HOST_USER", global_settings.EMAIL_HOST_USER),
    "EMAIL_PORT": os.getenv("EMAIL_PORT", global_settings.EMAIL_PORT),
    "EMAIL_SUBJECT_PREFIX": os.getenv(
        "EMAIL_SUBJECT_PREFIX", global_settings.EMAIL_SUBJECT_PREFIX
    ),
    "EMAIL_SSL_CERTFILE": os.getenv(
        "EMAIL_SSL_CERTFILE", global_settings.EMAIL_SSL_CERTFILE
    ),
    "EMAIL_SSL_KEYFILE": os.getenv(
        "EMAIL_SSL_KEYFILE", global_settings.EMAIL_SSL_KEYFILE
    ),
    "EMAIL_TIMEOUT": os.getenv("EMAIL_TIMEOUT", global_settings.EMAIL_TIMEOUT),
    "EMAIL_USE_LOCALTIME": os.getenv(
        "EMAIL_USE_LOCALTIME", global_settings.EMAIL_USE_LOCALTIME
    ),
    "EMAIL_USE_SSL": os.getenv("EMAIL_USE_SSL", global_settings.EMAIL_USE_SSL),
    "EMAIL_USE_TLS": os.getenv("EMAIL_USE_TLS", global_settings.EMAIL_USE_TLS),
    "LOGGING": {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
    },
    "INSTALLED_APPS": [
        "email_relay",
    ],
    "SERVER_EMAIL": os.getenv("SERVER_EMAIL", global_settings.SERVER_EMAIL),
}
if not DEBUG:
    SETTINGS["DATABASES"]["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

if __name__ == "__main__":
    settings.configure(**SETTINGS)
    django.setup()
    call_command("migrate")
    call_command("runrelay")
