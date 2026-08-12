from __future__ import annotations

import logging
import os

import pytest
from django.conf import settings

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS

from .settings import DEFAULT_SETTINGS

pytest_plugins = []  # type: ignore


def pytest_configure(config):
    logging.disable(logging.CRITICAL)

    DEFAULT_SETTINGS.pop("DATABASES", None)

    settings.configure(
        **DEFAULT_SETTINGS,
        **TEST_SETTINGS,
    )


def database_settings(name: str) -> dict[str, object]:
    if host := os.getenv("POSTGRES_HOST"):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": host,
            "NAME": name,
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


TEST_SETTINGS = {
    "DATABASES": {
        "default": database_settings("defaultdb"),
        EMAIL_RELAY_DATABASE_ALIAS: database_settings("relaydb"),
    },
    "DATABASE_ROUTERS": [
        "email_relay.db.EmailDatabaseRouter",
    ],
    "INSTALLED_APPS": [
        "django.contrib.contenttypes",
        "email_relay",
    ],
}


STORED_ATTACHMENT_FIXTURE = {
    "position": 0,
    "kind": "bytes",
    "filename": "fixture.bin",
    "content_type": "application/octet-stream",
    "content": b"stored bytes",
}


@pytest.fixture
def create_stored_attachment():
    # Imported here because conftest loads before `pytest_configure` runs
    # `settings.configure`.
    from model_bakery import baker

    def _create(message, fixture=STORED_ATTACHMENT_FIXTURE):
        return baker.make("email_relay.MessageAttachment", message=message, **fixture)

    return _create


@pytest.fixture
def create_stored_message(create_stored_attachment):
    from model_bakery import baker

    from email_relay.models import Status

    def _create(*, content=b"stored payload"):
        message = baker.make(
            "email_relay.Message",
            data={
                "subject": "Stored",
                "to": ["to@example.com"],
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            },
            status=Status.QUEUED,
        )
        create_stored_attachment(
            message, {**STORED_ATTACHMENT_FIXTURE, "content": content}
        )
        return message

    return _create
