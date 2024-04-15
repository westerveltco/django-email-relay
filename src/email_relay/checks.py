from __future__ import annotations

from django.conf import settings
from django.core.checks import Tags
from django.core.checks import Warning
from django.core.checks import register

from email_relay.db import EmailDatabaseRouter


@register(Tags.compatibility)
def check_for_deprecated_db_router(app_configs, **kwargs):
    if (
        "email_relay" in settings.INSTALLED_APPS
        and "email_relay.db.EmailDatabaseRouter" in settings.DATABASE_ROUTERS
    ):
        return [
            Warning(
                "The email_relay.db.EmailDatabaseRouter will potentially be deprecated in a future version.",
                hint="Please visit https://github.com/westerveltco/django-email-relay/issues/154 for more information.",
                obj=EmailDatabaseRouter,
                id="email_relay.W001",
            )
        ]
    return []
