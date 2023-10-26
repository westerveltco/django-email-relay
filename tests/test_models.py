from __future__ import annotations

import datetime
import base64

import pytest
from django.utils import timezone
from django.core.mail import EmailMessage, EmailMultiAlternatives
from model_bakery import baker

from email_relay.models import Message
from email_relay.models import Priority
from email_relay.models import Status


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_message():
    baker.make("email_relay.Message")
    assert Message.objects.all().count() == 1


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
            "from_email": "from@example.com",
            "recipient_list": ["to@example.com"],
        }

    def test_create_message(self, data):
        message = Message.objects.create(data=data)

        assert message.data == data
        assert message.priority == Priority.LOW
        assert message.status == Status.QUEUED
        assert message.retry_count == 0
        assert message.log == ""
        assert message.sent_at is None

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

    def test_email_with_plain_text_attachment(self):
        email = EmailMultiAlternatives(
            subject="Test",
            body="Test",
            from_email="from@example.com",
            to=["to@example.com"],
        )
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

    def test_email_with_binary_attachment(self, faker):
        email = EmailMultiAlternatives(
            subject="Test",
            body="Test",
            from_email="from@example.com",
            to=["to@example.com"],
        )
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

    def test_email_send(self, data, mailoutbox):
        message = Message.objects.create(data=data)
        email = EmailMultiAlternatives(
            subject="Test 2",
            body="Test 2",
            from_email="from2@example.com",
            to=["to2@example.com"],
        )
        message.email = email
        message.save()

        message.email.send()

        assert len(mailoutbox) == 1

    def test_email_send_with_plain_text_attachment(self, mailoutbox):
        email = EmailMultiAlternatives(
            subject="Test",
            body="Test",
            from_email="from@example.com",
            to=["to@example.com"],
        )
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

    def test_email_send_with_binary_attachment(self, faker, mailoutbox):
        email = EmailMultiAlternatives(
            subject="Test",
            body="Test",
            from_email="from@example.com",
            to=["to@example.com"],
        )
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
