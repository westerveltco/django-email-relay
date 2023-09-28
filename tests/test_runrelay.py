from __future__ import annotations

import datetime

import pytest
from django.core.management import call_command
from django.test.utils import override_settings
from django.utils import timezone
from model_bakery import baker

from email_relay.management.commands.runrelay import Command
from email_relay.models import Message
from email_relay.models import Status


def test_runrelay_help():
    # We'll capture the output of the command
    with pytest.raises(SystemExit) as exec_info:
        # call_command will execute our command as if we ran it from the command line
        # the 'stdout' argument captures the command output
        call_command("runrelay", "--help")

    # Asserting that the command exits with a successful exit code (0 for help command)
    assert exec_info.value.code == 0


@pytest.fixture
def runrelay():
    return Command()


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_delete_sent_messages_based_on_retention_default(runrelay):
    baker.make(
        "email_relay.Message",
        status=Status.SENT,
        sent_at=timezone.now(),
        _quantity=10,
    )

    runrelay.delete_old_messages()

    assert Message.objects.count() == 10


@override_settings(
    DJANGO_EMAIL_RELAY={
        "MESSAGES_RETENTION_SECONDS": 0,
    }
)
@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_delete_sent_messages_based_on_retention_zero(runrelay):
    baker.make(
        "email_relay.Message",
        status=Status.SENT,
        sent_at=timezone.now(),
        _quantity=10,
    )

    runrelay.delete_old_messages()

    assert Message.objects.count() == 0


@override_settings(
    DJANGO_EMAIL_RELAY={
        "MESSAGES_RETENTION_SECONDS": 600,
    }
)
@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_delete_sent_messages_based_on_retention_non_zero(runrelay):
    baker.make(
        "email_relay.Message",
        status=Status.SENT,
        sent_at=timezone.now(),
        _quantity=5,
    )
    baker.make(
        "email_relay.Message",
        status=Status.SENT,
        sent_at=timezone.now() - datetime.timedelta(seconds=601),
        _quantity=5,
    )

    runrelay.delete_old_messages()

    assert Message.objects.count() == 5
