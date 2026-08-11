from __future__ import annotations

import base64
import datetime
from email import policy
from email.message import EmailMessage as StandardEmailMessage
from email.mime.base import MIMEBase
from email.mime.message import MIMEMessage

import pytest
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.db import connections
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from model_bakery import baker

from email_relay.attachments import PersistedAttachmentError
from email_relay.models import Message
from email_relay.models import MessageAttachment
from email_relay.models import Priority
from email_relay.models import Status

STORED_MIME_CONTENT = (
    b"Content-Type: application/octet-stream\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Transfer-Encoding: base64\r\n"
    b'Content-Disposition: inline; filename="mime.bin"\r\n'
    b"Content-ID: <attachment@example.com>\r\n"
    b"X-Relay-Fixture: preserved\r\n"
    b"\r\n"
    b"bWltZSBwYXlsb2Fk\r\n"
)

STORED_ATTACHMENT_FIXTURE = {
    "position": 0,
    "kind": "bytes",
    "filename": "fixture.bin",
    "content_type": "application/octet-stream",
    "content": b"stored bytes",
}


def create_stored_attachment(message, fixture=STORED_ATTACHMENT_FIXTURE):
    return MessageAttachment.objects.create(
        message=message,
        position=fixture["position"],
        kind=fixture["kind"],
        filename=fixture["filename"],
        content_type=fixture["content_type"],
        content=fixture["content"],
    )


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

        with CaptureQueriesContext(connections["email_relay_db"]) as queries:
            message_batch = Message.objects.get_message_batch()

        assert len(message_batch) == 1
        assert any("LIMIT 1" in query["sql"] for query in queries)

    def test_get_message_for_sending(self):
        message = baker.make("email_relay.Message", status=Status.QUEUED)

        message_for_sending = Message.objects.get_message_for_sending(message.id)

        assert message_for_sending == message

    def test_get_message_for_sending_rejects_stale_batch_candidate(self):
        message = baker.make("email_relay.Message", status=Status.SENT)

        with pytest.raises(Message.DoesNotExist):
            Message.objects.get_message_for_sending(message.id)

    @pytest.mark.parametrize(
        ("status", "expected"),
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
        messages = baker.make("email_relay.Message", status=Status.SENT, _quantity=5)
        for message in messages:
            create_stored_attachment(message)

        with CaptureQueriesContext(connections["email_relay_db"]) as queries:
            deleted_messages = Message.objects.delete_all_sent_messages()

        assert deleted_messages == 5
        assert Message.objects.count() == 0
        assert MessageAttachment.objects.count() == 0
        selected_sql = " ".join(
            query["sql"]
            for query in queries
            if query["sql"].lstrip().upper().startswith("SELECT")
        )
        assert '"data"' not in selected_sql
        assert '"content"' not in selected_sql

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
            "body": "Test",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
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
        with CaptureQueriesContext(connections["email_relay_db"]) as queries:
            queued_message.defer()

        update = next(
            query["sql"]
            for query in queries
            if query["sql"].lstrip().upper().startswith("UPDATE")
        )
        assert queued_message.status == Status.DEFERRED
        assert '"data"' not in update

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
        assert email.body == data["body"]
        assert email.from_email == data["from_email"]
        assert email.to == data["to"]

    @pytest.mark.parametrize(
        ("content", "content_type", "expected"),
        [
            ("Hello World!", "text/plain", "Hello World!"),
            ("\ufeffcaf\u00e9", "text/plain", "\ufeffcaf\u00e9"),
            ("AP9wYXlsb2Fk", "application/zip", b"\x00\xffpayload"),
            ("dGVzdA==", "text/plain", "test"),
        ],
    )
    def test_literal_legacy_attachment_row(self, content, content_type, expected):
        message = Message.objects.create(
            data={
                "subject": "Legacy fixture",
                "body": "Body",
                "from_email": "from@example.com",
                "to": ["to@example.com"],
                "cc": [],
                "bcc": [],
                "reply_to": [],
                "extra_headers": {},
                "alternatives": [],
                "attachments": [
                    {
                        "filename": "fixture.bin",
                        "content": content,
                        "mimetype": content_type,
                    }
                ],
                "_email_relay_version": "0.6.0",
            }
        )

        assert message.email.attachments[0][1] == expected

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
        assert message.data["body"] == email.body
        assert message.data["from_email"] == email.from_email
        assert message.data["to"] == email.to

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

    def test_stored_message_with_no_attachments(self, data):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 0,
                },
            }
        )

        email = message.email

        assert email.subject == "Test"
        assert email.attachments == []

    def test_literal_stored_attachment(self, data):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message)

        email = message.email

        assert email.attachments[0][0] == "fixture.bin"
        assert email.attachments[0][1] == b"stored bytes"
        assert email.attachments[0][2] == "application/octet-stream"

    def test_stored_attachments_are_ordered_by_position(self, data):
        second = {
            "position": 1,
            "kind": "bytes",
            "filename": "second.bin",
            "content_type": "application/octet-stream",
            "content": b"second attachment",
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 2,
                },
            }
        )
        create_stored_attachment(message, second)
        create_stored_attachment(message)

        email = message.email

        assert [attachment[0] for attachment in email.attachments] == [
            "fixture.bin",
            "second.bin",
        ]

    def test_complete_stored_mime_attachment(self, data):
        fixture = {
            "position": 0,
            "kind": "mime",
            "filename": "mime.bin",
            "content_type": "application/octet-stream",
            "content": STORED_MIME_CONTENT,
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        email = message.email
        attached = email.attachments[0]
        email.message()

        assert attached.get_payload(decode=True) == b"mime payload"
        assert attached.get_filename() == "mime.bin"
        assert attached.get_content_type() == "application/octet-stream"
        assert attached["Content-Disposition"].startswith("inline")
        assert attached["Content-ID"] == "<attachment@example.com>"
        assert attached["X-Relay-Fixture"] == "preserved"

    def test_malformed_stored_mime_attachment_is_rejected(self, data):
        fixture = {
            "position": 0,
            "kind": "mime",
            "filename": None,
            "content_type": "text/plain",
            "content": b"not a serialized MIME entity",
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        with pytest.raises(PersistedAttachmentError, match="malformed"):
            _ = message.email

    def test_stored_message_rfc822_mime_attachment(self, data):
        nested = StandardEmailMessage()
        nested["Subject"] = "Nested message"
        nested["From"] = "nested@example.com"
        nested["To"] = "to@example.com"
        nested.set_content("Nested body")
        part = MIMEMessage(nested)
        part.add_header("Content-Disposition", "attachment", filename="nested.eml")
        content = part.as_bytes(policy=policy.SMTP)
        fixture = {
            "position": 0,
            "kind": "mime",
            "filename": "nested.eml",
            "content_type": "message/rfc822",
            "content": content,
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        email = message.email
        attached = email.attachments[0]
        email.message()

        assert attached.get_content_type() == "message/rfc822"
        assert attached.get_filename() == "nested.eml"
        assert attached.get_payload()[0]["Subject"] == "Nested message"

    def test_mixed_legacy_and_stored_sources_are_invalid(self, data):
        message = Message.objects.create(
            data={
                **data,
                "attachments": [],
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 0,
                },
            }
        )

        with pytest.raises(PersistedAttachmentError, match="both"):
            _ = message.email

    @pytest.mark.parametrize("count", [True, -1, "1"])
    def test_invalid_stored_count_is_rejected(self, data, count):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": count,
                },
            }
        )

        with pytest.raises(PersistedAttachmentError, match="nonnegative"):
            _ = message.email

    @pytest.mark.parametrize(
        "marker",
        [
            {},
            {"format": "stored-v1", "count": 0, "extra": True},
            [],
        ],
    )
    def test_invalid_stored_marker_is_rejected(self, data, marker):
        message = Message.objects.create(
            data={**data, "_email_relay_attachments": marker}
        )

        with pytest.raises(PersistedAttachmentError, match="Invalid"):
            _ = message.email

    def test_unknown_stored_format_is_invalid(self, data):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v2",
                    "count": 0,
                },
            }
        )

        with pytest.raises(PersistedAttachmentError, match="Unknown"):
            _ = message.email

    def test_stored_attachment_count_must_match_rows(self, data):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )

        with pytest.raises(PersistedAttachmentError, match="count"):
            _ = message.email

    def test_stored_attachment_positions_must_be_contiguous(self, data):
        fixture = {**STORED_ATTACHMENT_FIXTURE, "position": 1}
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        with pytest.raises(PersistedAttachmentError, match="positions"):
            _ = message.email

    @pytest.mark.parametrize(
        ("fixture", "match"),
        [
            ({**STORED_ATTACHMENT_FIXTURE, "kind": "unknown"}, "unknown kind"),
            ({**STORED_ATTACHMENT_FIXTURE, "content_type": ""}, "content type"),
        ],
    )
    def test_invalid_stored_attachment_metadata_is_rejected(self, data, fixture, match):
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        with pytest.raises(PersistedAttachmentError, match=match):
            _ = message.email

    @pytest.mark.parametrize(
        ("field", "value", "match"),
        [
            ("filename", "other.bin", "filename"),
            ("content_type", "application/pdf", "content type"),
        ],
    )
    def test_stored_mime_metadata_must_match_content(self, data, field, value, match):
        fixture = {
            "position": 0,
            "kind": "mime",
            "filename": "mime.bin",
            "content_type": "application/octet-stream",
            "content": STORED_MIME_CONTENT,
            field: value,
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        with pytest.raises(PersistedAttachmentError, match=match):
            _ = message.email

    def test_stored_attachment_positions_are_unique(self, data):
        message = Message.objects.create(data=data)
        create_stored_attachment(message)

        with pytest.raises(IntegrityError):
            create_stored_attachment(message)

    def test_stored_attachment_coerces_database_binary_value(self, data):
        fixture = {
            **STORED_ATTACHMENT_FIXTURE,
            "content": memoryview(b"database bytes"),
        }
        message = Message.objects.create(
            data={
                **data,
                "_email_relay_attachments": {
                    "format": "stored-v1",
                    "count": 1,
                },
            }
        )
        create_stored_attachment(message, fixture)

        assert message.email.attachments[0][1] == b"database bytes"

    def test_attachment_timestamps(self, data):
        message = Message.objects.create(data=data)
        attachment = create_stored_attachment(message)
        created_at = attachment.created_at
        updated_at = attachment.updated_at

        attachment.filename = "updated.bin"
        attachment.save(update_fields=["filename"])

        assert attachment.created_at == created_at
        assert attachment.updated_at > updated_at
