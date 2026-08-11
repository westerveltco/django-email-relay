from __future__ import annotations

import base64
from email.mime.base import MIMEBase

import pytest
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives

from email_relay import __version__
from email_relay.attachments import PersistedAttachmentError
from email_relay.email import RelayEmailData
from email_relay.email import relay_email_from_legacy_data
from email_relay.email import serialize_legacy_email


@pytest.fixture
def email_message():
    return EmailMessage(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )


def test_envelope_from_email_message(email_message):
    envelope = RelayEmailData.from_email_message(email_message)

    assert envelope == RelayEmailData(
        subject="Subject here",
        body="Here is the message.",
        from_email="from@example.com",
        to=["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        extra_headers={"Test-Header": "Test Value"},
        alternatives=[],
        _email_relay_version=__version__,
    )
    assert not hasattr(envelope, "attachments")


def test_envelope_from_email_message_with_alternative(email_message):
    email = EmailMultiAlternatives(
        subject=email_message.subject,
        body=email_message.body,
        from_email=email_message.from_email,
        to=email_message.to,
    )
    email.attach_alternative("<p>Here is the message.</p>", "text/html")

    envelope = RelayEmailData.from_email_message(email)

    assert envelope.alternatives == [("<p>Here is the message.</p>", "text/html")]


def test_serialize_legacy_email_without_attachments(email_message):
    data = serialize_legacy_email(email_message)

    assert data == {
        "subject": "Subject here",
        "body": "Here is the message.",
        "from_email": "from@example.com",
        "to": ["to@example.com"],
        "cc": ["cc@example.com"],
        "bcc": ["bcc@example.com"],
        "reply_to": ["reply_to@example.com"],
        "extra_headers": {"Test-Header": "Test Value"},
        "alternatives": [],
        "attachments": [],
        "_email_relay_version": __version__,
    }
    assert list(data)[-2:] == ["attachments", "_email_relay_version"]


def test_serialize_legacy_plain_text_attachment(email_message):
    email_message.attach("test.txt", b"Hello World!", "text/plain")

    data = serialize_legacy_email(email_message)

    assert data["attachments"] == [
        {
            "filename": "test.txt",
            "content": "Hello World!",
            "mimetype": "text/plain",
        }
    ]


def test_serialize_legacy_binary_attachment(email_message):
    email_message.attach("test.zip", b"\x00\xffpayload", "application/zip")

    data = serialize_legacy_email(email_message)

    assert data["attachments"] == [
        {
            "filename": "test.zip",
            "content": "AP9wYXlsb2Fk",
            "mimetype": "application/zip",
        }
    ]


def test_serialize_and_read_unnamed_legacy_attachment(email_message):
    email_message.attach(None, b"payload", "application/octet-stream")

    data = serialize_legacy_email(email_message)
    relay_email = relay_email_from_legacy_data(data)

    assert data["attachments"][0]["filename"] is None
    assert relay_email.attachments[0].filename is None
    assert relay_email.attachments[0].content == b"payload"


def test_serialize_legacy_mimebase_attachment(email_message):
    part = MIMEBase("application", "octet-stream")
    part["Content-Disposition"] = 'attachment; filename="test.bin"'
    part.set_payload(b"payload")
    email_message.attach(part)

    data = serialize_legacy_email(email_message)

    assert data["attachments"] == [
        {
            "filename": "test.bin",
            "content": base64.b64encode(b"payload").decode(),
            "mimetype": "application/octet-stream",
        }
    ]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Hello World!", b"Hello World!"),
        ("\ufeffcaf\u00e9", "\ufeffcaf\u00e9".encode()),
        ("AP9wYXlsb2Fk", b"\x00\xffpayload"),
        ("dGVzdA==", b"test"),
    ],
)
def test_literal_legacy_attachment_decoding(content, expected):
    relay_email = relay_email_from_legacy_data(
        {
            "subject": "Legacy",
            "body": "Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
            "cc": [],
            "bcc": [],
            "reply_to": [],
            "extra_headers": {},
            "alternatives": [],
            "_email_relay_version": "0.6.0",
            "attachments": [
                {
                    "filename": "fixture.bin",
                    "content": content,
                    "mimetype": "application/octet-stream",
                }
            ],
        }
    )

    assert relay_email.attachments[0].content == expected


def test_base64_looking_plain_text_keeps_legacy_ambiguous_meaning():
    relay_email = relay_email_from_legacy_data(
        {
            "attachments": [
                {
                    "filename": "ambiguous.txt",
                    "content": "dGVzdA==",
                    "mimetype": "text/plain",
                }
            ]
        }
    )

    assert relay_email.attachments[0].content == b"test"


def test_invalid_legacy_attachment_shape_fails_before_email_construction():
    with pytest.raises(PersistedAttachmentError, match="must be a list"):
        relay_email_from_legacy_data({"attachments": {}})
