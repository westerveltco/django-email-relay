from __future__ import annotations

import os
from typing import Any

import dj_database_url

from email_relay.conf import app_settings


def get_email_relay_database_settings(database_url: str) -> dict[str, Any]:
    return {app_settings.DATABASE_ALIAS: dj_database_url.parse(database_url)}


EMAIL_RELAY_DATABASE_SETTINGS = get_email_relay_database_settings(
    os.environ.get("EMAIL_RELAY_DATABASE_URL", "")
)


class EmailDatabaseRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "email_relay":
            return app_settings.DATABASE_ALIAS
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "email_relay":
            return app_settings.DATABASE_ALIAS
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
