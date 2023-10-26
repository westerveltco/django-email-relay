from __future__ import annotations

from email_relay.conf import app_settings


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
        if (
            obj1._meta.app_label == "email_relay"
            or obj2._meta.app_label == "email_relay"
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "email_relay":
            return db == app_settings.DATABASE_ALIAS
        return None
