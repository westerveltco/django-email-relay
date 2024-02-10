from __future__ import annotations

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.mail import mail_admins
from django.core.mail import mail_managers
from django.core.mail import send_mail
from django.core.mail import send_mass_mail
from django.test import override_settings

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS
from email_relay.models import Message

pytestmark = pytest.mark.django_db(databases=["default", EMAIL_RELAY_DATABASE_ALIAS])


@pytest.fixture(autouse=True, scope="module")
def relay_email_backend():
    with override_settings(
        EMAIL_BACKEND="email_relay.backend.RelayDatabaseEmailBackend",
    ):
        yield


def test_send_mail(mailoutbox):
    send_mail(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        html_message="<p>Here is the message.</p>",
    )

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == "Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == "from@example.com"
    assert email.to == ["to@example.com"]
    assert email.alternatives == [("<p>Here is the message.</p>", "text/html")]


def test_send_mass_mail(mailoutbox):
    send_mass_mail(
        (
            (
                "Subject here",
                "Here is the message.",
                "from@example.com",
                ["to@example.com"],
            ),
            (
                "Another subject",
                "Here is another message.",
                "from@example.com",
                ["to@example.com"],
            ),
        ),
    )

    assert Message.objects.count() == 2
    assert len(mailoutbox) == 0


@override_settings(ADMINS=[("Admin", "admin@example.com")])
def test_mail_admins(mailoutbox):
    mail_admins(
        "Subject here",
        "Here is the message.",
    )

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == f"{settings.EMAIL_SUBJECT_PREFIX}Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == settings.SERVER_EMAIL
    assert email.to == ["admin@example.com"]


@override_settings(MANAGERS=[("Manager", "manager@example.com")])
def test_mail_managers(mailoutbox):
    mail_managers(
        "Subject here",
        "Here is the message.",
    )

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == f"{settings.EMAIL_SUBJECT_PREFIX}Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == settings.SERVER_EMAIL
    assert email.to == ["manager@example.com"]


def test_emailmessage(mailoutbox):
    email_message = EmailMessage(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )

    email_message.send()

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == "Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == "from@example.com"
    assert email.to == ["to@example.com"]
    assert email.cc == ["cc@example.com"]
    assert email.bcc == ["bcc@example.com"]
    assert email.reply_to == ["reply_to@example.com"]
    assert email.extra_headers == {"Test-Header": "Test Value"}


def test_emailmessage_attach(mailoutbox):
    email_message = EmailMessage(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )
    email_message.attach("attachment.txt", "Here is the attachment.")

    email_message.send()

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == "Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == "from@example.com"
    assert email.to == ["to@example.com"]
    assert email.cc == ["cc@example.com"]
    assert email.bcc == ["bcc@example.com"]
    assert email.reply_to == ["reply_to@example.com"]
    assert email.extra_headers == {"Test-Header": "Test Value"}
    assert email.attachments == [
        ("attachment.txt", "Here is the attachment.", "text/plain"),
    ]


def test_emailmessage_attach_file(tmp_path, mailoutbox):
    email_message = EmailMessage(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )
    file_path = tmp_path / "attachment.txt"
    file_path.write_text("Here is the attachment.")
    email_message.attach_file(str(file_path))

    email_message.send()

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == "Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == "from@example.com"
    assert email.to == ["to@example.com"]
    assert email.cc == ["cc@example.com"]
    assert email.bcc == ["bcc@example.com"]
    assert email.reply_to == ["reply_to@example.com"]
    assert email.extra_headers == {"Test-Header": "Test Value"}
    assert email.attachments == [
        ("attachment.txt", "Here is the attachment.", "text/plain"),
    ]


def test_emailmessagealternatives(mailoutbox):
    email_multi_alternatives = EmailMultiAlternatives(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )
    email_multi_alternatives.attach_alternative(
        "<p>Here is the message.</p>", "text/html"
    )

    email_multi_alternatives.send()

    assert Message.objects.count() == 1
    assert len(mailoutbox) == 0

    email = Message.objects.get().email
    assert email.subject == "Subject here"
    assert email.body == "Here is the message."
    assert email.from_email == "from@example.com"
    assert email.to == ["to@example.com"]
    assert email.cc == ["cc@example.com"]
    assert email.bcc == ["bcc@example.com"]
    assert email.reply_to == ["reply_to@example.com"]
    assert email.extra_headers == {"Test-Header": "Test Value"}
    assert email.alternatives == [
        ("<p>Here is the message.</p>", "text/html"),
    ]
