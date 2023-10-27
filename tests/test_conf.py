from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings

from email_relay.conf import app_settings


@pytest.mark.parametrize(
    "setting,default_setting",
    [
        ("DATABASE_ALIAS", "email_relay_db"),
        ("EMAIL_MAX_BATCH", None),
        ("EMAIL_MAX_DEFERRED", None),
        ("EMAIL_MAX_RETRIES", None),
        ("EMPTY_QUEUE_SLEEP", 30),
        ("EMAIL_THROTTLE", 0),
        ("MESSAGES_BATCH_SIZE", None),
        ("MESSAGES_RETENTION_SECONDS", None),
        ("RELAY_HEALTHCHECK_METHOD", "GET"),
        ("RELAY_HEALTHCHECK_STATUS_CODE", 200),
        ("RELAY_HEALTHCHECK_TIMEOUT", 5.0),
        ("RELAY_HEALTHCHECK_URL", None),
    ],
)
def test_default_settings(setting, default_setting):
    user_settings = getattr(settings, "DJANGO_EMAIL_RELAY", {})

    assert user_settings == {}
    assert getattr(app_settings, setting) == default_setting


@pytest.mark.parametrize(
    "setting,user_setting",
    [
        ("DATABASE_ALIAS", "custom_db_name"),
        ("EMAIL_MAX_BATCH", 10),
        ("EMAIL_MAX_DEFERRED", 10),
        ("EMAIL_MAX_RETRIES", 10),
        ("EMPTY_QUEUE_SLEEP", 1),
        ("EMAIL_THROTTLE", 1),
        ("MESSAGES_BATCH_SIZE", 10),
        ("MESSAGES_RETENTION_SECONDS", 10),
        ("RELAY_HEALTHCHECK_METHOD", "POST"),
        ("RELAY_HEALTHCHECK_STATUS_CODE", 201),
        ("RELAY_HEALTHCHECK_TIMEOUT", 10.0),
        ("RELAY_HEALTHCHECK_URL", "http://example.com/healthcheck"),
    ],
)
def test_custom_settings(setting, user_setting):
    with override_settings(
        DJANGO_EMAIL_RELAY={
            setting: user_setting,
        },
    ):
        assert getattr(app_settings, setting) == user_setting
