from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

EMAIL_RELAY_SETTINGS_NAME = "DJANGO_EMAIL_RELAY"
EMAIL_RELAY_DATABASE_ALIAS = "email_relay_db"


@dataclass
class AppSettings:
    DATABASE_ALIAS: str = EMAIL_RELAY_DATABASE_ALIAS
    EMAIL_MAX_BATCH: int | None = None
    EMAIL_MAX_DEFERRED: int | None = None
    EMAIL_MAX_RETRIES: int | None = None
    EMPTY_QUEUE_SLEEP: int = 30
    EMAIL_THROTTLE: int = 0
    MESSAGES_BATCH_SIZE: int | None = None
    MESSAGES_RETENTION_SECONDS: int | None = None

    def __getattribute__(self, __name: str) -> Any:
        user_settings = getattr(settings, EMAIL_RELAY_SETTINGS_NAME, {})
        return user_settings.get(__name, super().__getattribute__(__name))


app_settings = AppSettings()
