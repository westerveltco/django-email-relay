from __future__ import annotations

import importlib

import pytest
from django.apps import apps
from django.db import connections
from model_bakery import baker

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS
from email_relay.models import Message


@pytest.fixture
def migrate_message_data_to_new_schema():
    return importlib.import_module(
        "email_relay.migrations.0002_auto_20231030_1304"
    ).migrate_message_data_to_new_schema


@pytest.mark.django_db(databases=["default", EMAIL_RELAY_DATABASE_ALIAS])
def test_migrate_message_data_to_new_schema(migrate_message_data_to_new_schema):
    class MockSchemaEditor:
        connection = connections[EMAIL_RELAY_DATABASE_ALIAS]

    baker.make(
        "email_relay.Message",
        data={
            "message": "Here is the message.",
            "recipient_list": ["to@example.com"],
            "html_message": "<p>HTML</p>",
        },
        _quantity=3,
    )

    for message in Message.objects.all():
        assert message.data["message"] == "Here is the message."
        assert message.data["recipient_list"] == ["to@example.com"]
        assert message.data["html_message"] == "<p>HTML</p>"
        assert not message.data.get("to")
        assert not message.data.get("cc")
        assert not message.data.get("bcc")
        assert not message.data.get("reply_to")
        assert not message.data.get("extra_headers")
        assert not message.data.get("alternatives")

    migrate_message_data_to_new_schema(apps, MockSchemaEditor())

    assert Message.objects.count() == 3

    for message in Message.objects.all():
        assert not message.data.get("message")
        assert not message.data.get("recipient_list")
        assert not message.data.get("html_message")
        assert message.data["body"] == "Here is the message."
        assert message.data["to"] == ["to@example.com"]
        assert message.data["cc"] == []
        assert message.data["bcc"] == []
        assert message.data["reply_to"] == []
        assert message.data["extra_headers"] == {}
        assert message.data["alternatives"] == [
            ["<p>HTML</p>", "text/html"],
        ]
