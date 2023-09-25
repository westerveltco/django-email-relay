from __future__ import annotations

import os
from typing import Any

import dj_database_url
import django
from django.conf import settings
from django.core.management import call_command


def get_user_settings_from_env() -> dict[str, Any]:
    all_env_vars = {k: v for k, v in os.environ.items()}
    return env_vars_to_nested_dict(all_env_vars)


def env_vars_to_nested_dict(env_vars: dict[str, Any]) -> dict[str, Any]:
    config = {}
    for key, value in env_vars.items():
        keys = key.split("__")
        d = config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
    return config


def merge_dicts(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    for key, value in dict2.items():
        if isinstance(value, dict) and isinstance(dict1.get(key), dict):
            merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1


default_settings = {
    "DATABASES": {
        "default": dj_database_url.parse(os.getenv("DATABASE_URL", "sqlite://:memory:"))
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
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
    },
    "INSTALLED_APPS": [
        "email_relay",
    ],
}


def main() -> None:
    user_settings = get_user_settings_from_env()
    SETTINGS = merge_dicts(default_settings, user_settings)

    settings.configure(**SETTINGS)
    django.setup()
    call_command("migrate")
    call_command("runrelay")


if __name__ == "__main__":
    raise SystemExit(main())
