from __future__ import annotations

from django.apps import AppConfig
from django.conf import global_settings
from django.conf import settings

try:
    from environs import Env
except ImportError:
    Env = None


class EmailRelayConfig(AppConfig):
    name = "email_relay"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from email_relay.conf import app_settings

        if not app_settings.ENABLE_AUTO_SETUP:
            return

        if (
            settings.EMAIL_BACKEND is None
            or settings.EMAIL_BACKEND == global_settings.EMAIL_BACKEND
        ):
            settings.EMAIL_BACKEND = "email_relay.backend.EmailRelayBackend"

        if app_settings.DATABASE_ALIAS not in settings.DATABASES and Env is not None:
            env = Env()

            settings.DATABASES[app_settings.DATABASE_ALIAS] = env.dj_db_url(
                "EMAIL_RELAY_DATABASE_URL", default="sqlite://:memory:"
            )

        if "email_relay.db.EmailDatabaseRouter" not in settings.DATABASE_ROUTERS:
            settings.DATABASE_ROUTERS.append("email_relay.db.EmailDatabaseRouter")
