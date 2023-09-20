from __future__ import annotations

from django.conf import settings
from django.test import override_settings

from email_relay.conf import app_settings


def test_default_settings():
    user_settings = getattr(settings, "DJANGO_EMAIL_RELAY", {})

    assert user_settings == {}
    assert app_settings.DATABASE_ALIAS == "email_relay_db"
    assert app_settings.MESSAGES_BATCH_SIZE is None
    assert app_settings.EMAIL_MAX_RETRIES is None


@override_settings(
    DJANGO_EMAIL_RELAY={
        "DATABASE_ALIAS": "custom_db_name",
    },
)
def test_custom_database_alias():
    assert app_settings.DATABASE_ALIAS == "custom_db_name"


@override_settings(
    DJANGO_EMAIL_RELAY={
        "MESSAGES_BATCH_SIZE": 10,
    },
)
def test_custom_batch_size():
    assert app_settings.MESSAGES_BATCH_SIZE == 10


@override_settings(
    DJANGO_EMAIL_RELAY={
        "EMAIL_MAX_RETRIES": 5,
    },
)
def test_custom_max_retries():
    assert app_settings.EMAIL_MAX_RETRIES == 5
