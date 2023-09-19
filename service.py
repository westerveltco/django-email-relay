from __future__ import annotations

import os

import dj_database_url
import django
from django.conf import settings
from django.core.management import call_command

SETTINGS = {
    "DEBUG": os.getenv("EMAIL_RELAY_DEBUG", False),
    "DATABASES": {
        "default": dj_database_url.parse(os.getenv("EMAIL_RELAY_DATABASE_URL", "")),
    },
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
            "level": os.getenv("EMAIL_RELAY_LOG_LEVEL", "INFO"),
        },
    },
    "INSTALLED_APPS": [
        "email_relay",
    ],
}

if __name__ == "__main__":
    settings.configure(**SETTINGS)
    django.setup()
    call_command("migrate")
    call_command("runrelay")
