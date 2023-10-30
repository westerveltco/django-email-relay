from __future__ import annotations

import base64
import datetime
from email.mime.base import MIMEBase

import pytest
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.test import override_settings
from django.utils import timezone
from model_bakery import baker

from email_relay.models import Message
from email_relay.models import Priority
from email_relay.models import Status


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_message():
    baker.make("email_relay.Message")
    assert Message.objects.all().count() == 1


@pytest.mark.django_db(databases=["default", "email_relay_db"])
class TestMessageManager:
    def test_get_message_batch(self):
        baker.make("email_relay.Message", status=Status.QUEUED, _quantity=5)
        baker.make("email_relay.Message", status=Status.DEFERRED, _quantity=5)

        message_batch = Message.objects.get_message_batch()

        assert len(message_batch) == 10

    @override_settings(
        DJANGO_EMAIL_RELAY={
            "EMAIL_MAX_BATCH": 1,
        }
    )
    def test_get_message_batch_with_max_batch_size(self):
        baker.make("email_relay.Message", status=Status.QUEUED, _quantity=5)
        baker.make("email_relay.Message", status=Status.DEFERRED, _quantity=5)

        message_batch = Message.objects.get_message_batch()

        assert len(message_batch) == 1

    def test_get_message_for_sending(self):
        message = baker.make("email_relay.Message", status=Status.QUEUED)

        message_for_sending = Message.objects.get_message_for_sending(message.id)

        assert message_for_sending == message

    @pytest.mark.parametrize(
        "status, expected",
        [
            (Status.QUEUED, True),
            (Status.DEFERRED, True),
            (Status.FAILED, False),
            (Status.SENT, False),
        ],
    )
    def test_messages_available_to_send(self, status, expected):
        baker.make("email_relay.Message", status=status)

        assert Message.objects.messages_available_to_send() == expected

    def test_messages_available_to_send_with_no_messages(self):
        assert not Message.objects.messages_available_to_send()

    def test_delete_all_sent_messages(self):
        baker.make("email_relay.Message", status=Status.SENT, _quantity=5)

        deleted_messages = Message.objects.delete_all_sent_messages()

        assert deleted_messages == 5
        assert Message.objects.count() == 0

    def test_delete_messages_sent_before(self):
        one_week = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now() - datetime.timedelta(days=7),
        )
        now = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now(),
        )
        not_sent = baker.make(
            "email_relay.Message",
            status=Status.QUEUED,
            sent_at=None,
        )

        deleted_messages = Message.objects.delete_messages_sent_before(
            timezone.now() - datetime.timedelta(days=1)
        )

        assert deleted_messages == 1
        assert Message.objects.count() == 2

        messages = Message.objects.all()
        assert one_week not in messages
        assert now in messages
        assert not_sent in messages


@pytest.mark.django_db(databases=["default", "email_relay_db"])
class TestMessageQuerySet:
    @pytest.fixture
    def messages_with_priority(self):
        low = baker.make("email_relay.Message", priority=Priority.LOW)
        medium = baker.make("email_relay.Message", priority=Priority.MEDIUM)
        high = baker.make("email_relay.Message", priority=Priority.HIGH)
        return {
            "low": low,
            "medium": medium,
            "high": high,
        }

    @pytest.fixture
    def messages_with_status(self):
        queued = baker.make("email_relay.Message", status=Status.QUEUED)
        deferred = baker.make("email_relay.Message", status=Status.DEFERRED)
        failed = baker.make("email_relay.Message", status=Status.FAILED)
        sent = baker.make("email_relay.Message", status=Status.SENT)
        return {
            "queued": queued,
            "deferred": deferred,
            "failed": failed,
            "sent": sent,
        }

    def test_prioritized(self, messages_with_priority):
        queryset = Message.objects.prioritized()

        assert queryset.count() == 3
        assert queryset[0] == messages_with_priority["high"]
        assert queryset[1] == messages_with_priority["medium"]
        assert queryset[2] == messages_with_priority["low"]

    def test_high_priority(self, messages_with_priority):
        queryset = Message.objects.high_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["high"]

    def test_medium_priority(self, messages_with_priority):
        queryset = Message.objects.medium_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["medium"]

    def test_low_priority(self, messages_with_priority):
        queryset = Message.objects.low_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["low"]

    def test_queued(self, messages_with_status):
        queryset = Message.objects.queued()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["queued"]

    def test_deferred(self, messages_with_status):
        queryset = Message.objects.deferred()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["deferred"]

    def test_failed(self, messages_with_status):
        queryset = Message.objects.failed()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["failed"]

    def test_sent(self, messages_with_status):
        queryset = Message.objects.sent()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["sent"]

    def test_sent_before(self):
        one_week = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now() - datetime.timedelta(days=7),
        )
        now = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now(),
        )
        not_sent = baker.make(
            "email_relay.Message",
            status=Status.QUEUED,
            sent_at=None,
        )

        queryset = Message.objects.sent_before(
            timezone.now() - datetime.timedelta(days=1)
        )

        assert queryset.count() == 1
        assert one_week in queryset
        assert now not in queryset
        assert not_sent not in queryset


@pytest.mark.django_db(databases=["default", "email_relay_db"])
class TestMessageModel:
    @pytest.fixture
    def data(self):
        return {
            "subject": "Test",
            "message": "Test",
            "html_message": "<p>Test</p>",
            "from_email": "from@example.com",
            "recipient_list": ["to@example.com"],
        }

    @pytest.fixture
    def email(self):
        return EmailMultiAlternatives(
            subject="Test",
            body="Test",
            from_email="from@example.com",
            to=["to@example.com"],
        )

    @pytest.fixture
    def queued_message(self, data):
        return baker.make("email_relay.Message", data=data, status=Status.QUEUED)

    def test_create(self, data):
        message = baker.make("email_relay.Message", data=data)

        assert message.data == data
        assert message.priority == Priority.LOW
        assert message.status == Status.QUEUED
        assert message.retry_count == 0
        assert message.log == ""
        assert message.sent_at is None

    def test_str(self, data):
        message = baker.make("email_relay.Message", data=data)

        assert data["subject"] in str(message)

    def test_str_invalid_data(self):
        message = baker.make("email_relay.Message", data={})

        assert "invalid message" in str(message)

    def test_update_with_update_fields(self, data):
        message = baker.make("email_relay.Message", data=data)
        updated_at_original = message.updated_at

        message.retry_count = 1
        message.save(update_fields=["retry_count"])

        assert message.updated_at != updated_at_original

    def test_mark_sent(self, queued_message):
        queued_message.mark_sent()

        assert queued_message.status == Status.SENT

    def test_defer(self, queued_message):
        queued_message.defer()

        assert queued_message.status == Status.DEFERRED

    def test_fail(self, queued_message):
        queued_message.fail()

        assert queued_message.status == Status.FAILED

    def test_no_data(self):
        message = baker.make("email_relay.Message", data={})

        assert message.data == {}
        assert message.email is None

    def test_email_property(self, data):
        message = Message.objects.create(data=data)

        email = message.email

        assert isinstance(email, EmailMessage)
        assert email.subject == data["subject"]
        assert email.body == data["message"]
        assert email.from_email == data["from_email"]
        assert email.to == data["recipient_list"]

    def test_email_setter(self, data):
        message = Message.objects.create(data=data)
        email = EmailMultiAlternatives(
            subject="Test 2",
            body="Test 2",
            from_email="from2@example.com",
            to=["to2@example.com"],
        )

        message.email = email
        message.save()

        assert message.data["subject"] == email.subject
        assert message.data["message"] == email.body
        assert message.data["from_email"] == email.from_email
        assert message.data["recipient_list"] == email.to

    def test_email_with_plain_text_attachment(self, email):
        attachment_content = b"Hello World!"
        email.attach(
            filename="test.txt",
            content=attachment_content,
            mimetype="text/plain",
        )

        message = Message()
        message.email = email
        message.save()

        assert Message.objects.count() == 1

        saved_message = Message.objects.first()
        assert saved_message.data["attachments"][0]["filename"] == "test.txt"
        assert saved_message.data["attachments"][0][
            "content"
        ] == attachment_content.decode("utf-8")
        assert saved_message.data["attachments"][0]["mimetype"] == "text/plain"

        email_from_db = saved_message.email
        assert email_from_db.attachments[0][0] == "test.txt"
        assert email_from_db.attachments[0][1] == attachment_content.decode("utf-8")
        assert email_from_db.attachments[0][2] == "text/plain"

    def test_email_with_binary_attachment(self, email, faker):
        attachment_content = faker.binary(length=10)
        email.attach(
            filename="test.zip",
            content=attachment_content,
            mimetype="application/zip",
        )

        message = Message()
        message.email = email
        message.save()

        assert Message.objects.count() == 1

        saved_message = Message.objects.first()
        assert saved_message.data["attachments"][0]["filename"] == "test.zip"
        assert saved_message.data["attachments"][0]["content"] == base64.b64encode(
            attachment_content
        ).decode("utf-8")
        assert saved_message.data["attachments"][0]["mimetype"] == "application/zip"

        email_from_db = saved_message.email
        assert email_from_db.attachments[0][0] == "test.zip"
        assert email_from_db.attachments[0][1] == attachment_content
        assert email_from_db.attachments[0][2] == "application/zip"

    def test_email_with_mimebase_attachment(self, email):
        attachment_content = b"Hello World!"
        attachment = MIMEBase("application", "octet-stream")
        attachment["Content-Disposition"] = 'attachment; filename="test.txt"'
        attachment.set_payload(attachment_content)
        email.attach(attachment)

        message = Message()
        message.email = email
        message.save()

        assert Message.objects.count() == 1

        saved_message = Message.objects.first()
        assert saved_message.data["attachments"][0]["filename"] == "test.txt"
        assert saved_message.data["attachments"][0]["content"] == base64.b64encode(
            attachment_content
        ).decode("utf-8")
        assert (
            saved_message.data["attachments"][0]["mimetype"]
            == "application/octet-stream"
        )

        email_from_db = saved_message.email
        assert email_from_db.attachments[0][0] == "test.txt"
        assert email_from_db.attachments[0][1] == attachment_content
        assert email_from_db.attachments[0][2] == "application/octet-stream"

    def test_email_send(self, email, mailoutbox):
        message = Message()
        message.email = email
        message.save()

        message.email.send()

        assert len(mailoutbox) == 1

    def test_email_send_with_plain_text_attachment(self, email, mailoutbox):
        email.attach(
            filename="test.txt",
            content=b"Hello World!",
            mimetype="text/plain",
        )
        message = Message()
        message.email = email
        message.save()

        message.email.send()

        assert len(mailoutbox) == 1

    def test_email_send_with_binary_attachment(self, email, faker, mailoutbox):
        email.attach(
            filename="test.zip",
            content=faker.binary(length=10),
            mimetype="application/zip",
        )
        message = Message()
        message.email = email
        message.save()

        message.email.send()

        assert len(mailoutbox) == 1

    def test_email_send_with_mimebase_attachment(self, email, mailoutbox):
        attachment = MIMEBase("application", "octet-stream")
        attachment["Content-Disposition"] = 'attachment; filename="test.txt"'
        attachment.set_payload(b"Hello World!")
        email.attach(attachment)

        message = Message()
        message.email = email
        message.save()

        message.email.send()

        assert len(mailoutbox) == 1
