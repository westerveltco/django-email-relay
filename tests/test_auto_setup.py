from __future__ import annotations

import pytest
from django.apps import apps
from django.conf import settings
from django.test.utils import override_settings

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS


@pytest.fixture(autouse=True, scope="module")
def auto_setup_setting():
    with override_settings(
        DJANGO_EMAIL_RELAY={
            "ENABLE_AUTO_SETUP": True,
        },
    ):
        yield


@pytest.fixture
def app_config():
    return apps.get_app_config("email_relay")


@override_settings(EMAIL_BACKEND=None)
def test_auto_setup_email_backend(app_config):
    app_config.ready()

    assert settings.EMAIL_BACKEND == "email_relay.backend.EmailRelayBackend"


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    },
)
def test_auto_setup_database(app_config):
    app_config.ready()

    assert EMAIL_RELAY_DATABASE_ALIAS in settings.DATABASES


def test_auto_setup_database_router(app_config):
    app_config.ready()

    assert "email_relay.db.EmailDatabaseRouter" in settings.DATABASE_ROUTERS
