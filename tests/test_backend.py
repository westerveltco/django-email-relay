from __future__ import annotations

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.test.utils import override_settings

from email_relay.models import Message


@pytest.fixture(scope="module", autouse=True)
def relay_backend():
    with override_settings(
        EMAIL_BACKEND="email_relay.backend.RelayDatabaseEmailBackend"
    ):
        yield


def test_fixture():
    assert settings.EMAIL_BACKEND == "email_relay.backend.RelayDatabaseEmailBackend"


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_send_mail():
    assert Message.objects.count() == 0

    send_mail(
        "Subject here",
        "Here is the message.",
        "from_test@example.com",
        ["to_test@example.com"],
    )

    assert Message.objects.count() == 1


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_email_message():
    assert Message.objects.count() == 0

    email = EmailMessage(
        "Subject here",
        "Here is the message.",
        "from_test@example.com",
        ["to_test@example.com"],
    )

    email.send()

    assert Message.objects.count() == 1
