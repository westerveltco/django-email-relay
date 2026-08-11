from __future__ import annotations

from django.apps import AppConfig


class EmailRelayConfig(AppConfig):
    name = "email_relay"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from email_relay import checks  # noqa: F401
