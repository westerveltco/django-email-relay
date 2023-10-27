from __future__ import annotations

import django
from django.conf import settings
from django.core.management import call_command
from environs import Env

from .utils import get_user_settings_from_env
from .utils import merge_with_defaults

env = Env()

default_settings = {
    "DATABASES": {
        "default": env.dj_db_url("DATABASE_URL", default="sqlite://:memory:")
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
            "level": env("LOG_LEVEL", "INFO"),
        },
    },
    "INSTALLED_APPS": [
        "email_relay",
    ],
}


def main() -> int:
    """Main entrypoint for the email relay service, designed to be run independently of a Django project.

    Returns:
        int: Exit code. Should always return 0 as `runrelay` is expected to run indefinitely.
    """
    user_settings = get_user_settings_from_env()
    SETTINGS = merge_with_defaults(default_settings, user_settings)
    settings.configure(**SETTINGS)
    django.setup()
    call_command("migrate")
    call_command("runrelay")
    # should never get here, `runrelay` is an infinite loop
    # but if it does, exit with 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
