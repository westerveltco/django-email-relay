from __future__ import annotations

import datetime
import logging
from unittest import mock

import pytest
import responses
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


@override_settings(
    DJANGO_EMAIL_RELAY={
        "RELAY_HEALTHCHECK_URL": "http://example.com/healthcheck",
    }
)
@responses.activate
def test_relay_healthcheck_url(runrelay, caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(responses.GET, "http://example.com/healthcheck", status=200)

    runrelay.ping_healthcheck()

    assert len(responses.calls) == 1
    assert "healthcheck ping successful" in caplog.text


@responses.activate
def test_relay_healthcheck_url_not_configured(runrelay):
    responses.add(responses.GET, "http://example.com/healthcheck", status=200)

    runrelay.ping_healthcheck()

    assert len(responses.calls) == 0


@override_settings(
    DJANGO_EMAIL_RELAY={
        "RELAY_HEALTHCHECK_URL": "http://example.com/healthcheck",
        "RELAY_HEALTHCHECK_STATUS_CODE": 201,
    }
)
@responses.activate
def test_relay_healthcheck_status_code(runrelay, caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(responses.GET, "http://example.com/healthcheck", status=201)

    runrelay.ping_healthcheck()

    assert len(responses.calls) == 1
    assert "healthcheck ping successful" in caplog.text


@override_settings(
    DJANGO_EMAIL_RELAY={
        "RELAY_HEALTHCHECK_URL": "http://example.com/healthcheck",
        "RELAY_HEALTHCHECK_METHOD": "POST",
    }
)
@responses.activate
def test_relay_healthcheck_method(runrelay, caplog):
    caplog.set_level(logging.DEBUG)
    responses.add(responses.POST, "http://example.com/healthcheck", status=200)

    runrelay.ping_healthcheck()

    assert len(responses.calls) == 1
    assert "healthcheck ping successful" in caplog.text


@override_settings(
    DJANGO_EMAIL_RELAY={
        "RELAY_HEALTHCHECK_URL": "http://example.com/healthcheck",
    }
)
@responses.activate
def test_relay_healthcheck_failure(runrelay, caplog):
    caplog.set_level(logging.WARNING)
    responses.add(responses.GET, "http://example.com/healthcheck", status=500)

    runrelay.ping_healthcheck()

    assert len(responses.calls) == 1
    assert "healthcheck ping successful" not in caplog.text


@override_settings(
    DJANGO_EMAIL_RELAY={
        "RELAY_HEALTHCHECK_URL": "http://example.com/healthcheck",
    }
)
def test_relay_healthcheck_no_requests(runrelay, caplog):
    caplog.set_level(logging.WARNING)

    with mock.patch("email_relay.management.commands.runrelay.requests", None):
        runrelay.ping_healthcheck()

    assert "Healthcheck URL configured but requests is not installed." in caplog.text
