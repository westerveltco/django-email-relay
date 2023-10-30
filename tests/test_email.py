from __future__ import annotations

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives

from email_relay.email import RelayEmailData


def test_from_email_message():
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

    relay_email_data = RelayEmailData.from_email_message(email_message)

    assert relay_email_data.subject == email_message.subject
    assert relay_email_data.body == email_message.body
    assert relay_email_data.from_email == email_message.from_email
    assert relay_email_data.to == email_message.to
    assert relay_email_data.cc == email_message.cc
    assert relay_email_data.bcc == email_message.bcc
    assert relay_email_data.reply_to == email_message.reply_to
    assert relay_email_data.extra_headers == email_message.extra_headers
    assert relay_email_data.alternatives == []
    assert relay_email_data.attachments == []


def test_from_email_message_multi_alternatives():
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

    relay_email_data = RelayEmailData.from_email_message(email_multi_alternatives)

    assert relay_email_data.subject == email_multi_alternatives.subject
    assert relay_email_data.body == email_multi_alternatives.body
    assert relay_email_data.from_email == email_multi_alternatives.from_email
    assert relay_email_data.to == email_multi_alternatives.to
    assert relay_email_data.cc == email_multi_alternatives.cc
    assert relay_email_data.bcc == email_multi_alternatives.bcc
    assert relay_email_data.reply_to == email_multi_alternatives.reply_to
    assert relay_email_data.extra_headers == email_multi_alternatives.extra_headers
    assert relay_email_data.alternatives == email_multi_alternatives.alternatives
    assert relay_email_data.attachments == []


def test_to_dict():
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

    email_dict = RelayEmailData.from_email_message(email_message).to_dict()

    assert email_dict == {
        "subject": email_message.subject,
        "body": email_message.body,
        "from_email": email_message.from_email,
        "to": email_message.to,
        "cc": email_message.cc,
        "bcc": email_message.bcc,
        "reply_to": email_message.reply_to,
        "extra_headers": email_message.extra_headers,
        "alternatives": [],
        "attachments": [],
    }


def test_to_dict_multi_alternatives():
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

    email_dict = RelayEmailData.from_email_message(email_multi_alternatives).to_dict()

    assert email_dict == {
        "subject": email_multi_alternatives.subject,
        "body": email_multi_alternatives.body,
        "from_email": email_multi_alternatives.from_email,
        "to": email_multi_alternatives.to,
        "cc": email_multi_alternatives.cc,
        "bcc": email_multi_alternatives.bcc,
        "reply_to": email_multi_alternatives.reply_to,
        "extra_headers": email_multi_alternatives.extra_headers,
        "alternatives": email_multi_alternatives.alternatives,
        "attachments": [],
    }


def test_to_dict_with_attachment():
    email = EmailMessage(
        "Subject here",
        "Here is the message.",
        "from@example.com",
        ["to@example.com"],
        cc=["cc@example.com"],
        bcc=["bcc@example.com"],
        reply_to=["reply_to@example.com"],
        headers={"Test-Header": "Test Value"},
    )
    attachment_content = b"Hello World!"
    email.attach(
        filename="test.txt",
        content=attachment_content,
        mimetype="text/plain",
    )

    email_dict = RelayEmailData.from_email_message(email).to_dict()

    assert email_dict == {
        "subject": email.subject,
        "body": email.body,
        "from_email": email.from_email,
        "to": email.to,
        "cc": email.cc,
        "bcc": email.bcc,
        "reply_to": email.reply_to,
        "extra_headers": email.extra_headers,
        "alternatives": [],
        "attachments": [
            {
                "filename": "test.txt",
                "content": attachment_content.decode(),
                "mimetype": "text/plain",
            }
        ],
    }
