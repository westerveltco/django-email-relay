from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

EMAIL_RELAY_DATABASE_ALIAS = "email_relay_db"


@dataclass
class AppSettings:
    DATABASE_ALIAS: str = EMAIL_RELAY_DATABASE_ALIAS
    EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_MAX_BATCH: int | None = None
    EMAIL_MAX_DEFERRED: int | None = None
    EMAIL_MAX_RETRIES: int | None = None
    EMPTY_QUEUE_SLEEP: int = 30
    EMAIL_THROTTLE: int = 0
    MESSAGES_BATCH_SIZE: int | None = None

    def __getattribute__(self, __name: str) -> Any:
        user_settings = getattr(settings, "DJANGO_EMAIL_RELAY", {})
        return user_settings.get(__name, super().__getattribute__(__name))


app_settings = AppSettings()
