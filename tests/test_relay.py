from __future__ import annotations

import logging
import smtplib
from unittest import mock

import pytest
from django.core.mail import EmailMultiAlternatives
from django.db import InterfaceError
from django.db import OperationalError
from django.db import connections
from django.db import transaction
from django.test import override_settings
from model_bakery import baker

from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS
from email_relay.models import Message
from email_relay.models import MessageAttachment
from email_relay.models import Priority
from email_relay.models import Status
from email_relay.relay import send_all

pytestmark = pytest.mark.django_db(databases=["default", EMAIL_RELAY_DATABASE_ALIAS])


@pytest.fixture(autouse=True)
def caplog_level(caplog):
    with caplog.at_level(logging.DEBUG):
        yield


def test_send_all_empty_queue(mailoutbox, caplog):
    send_all()

    assert len(mailoutbox) == 0
    assert Message.objects.count() == 0
    assert "sending emails" in caplog.text
    assert "sent 0 emails, deferred 0 emails, failed 0 emails" in caplog.text


def test_send_all_single_message(mailoutbox, caplog):
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Test Subject"
    assert mailoutbox[0].to == ["to@example.com"]

    queued.refresh_from_db()

    assert queued.status == Status.SENT
    assert queued.sent_at is not None

    assert f"sent message {queued.id}" in caplog.text
    assert "sent 1 emails, deferred 0 emails, failed 0 emails" in caplog.text


def test_send_all_multiple_messages(mailoutbox, caplog):
    high_priority = baker.make(
        "email_relay.Message",
        data={"subject": "High Priority", "to": ["high@example.com"]},
        status=Status.QUEUED,
        priority=Priority.HIGH,
    )
    low_priority = baker.make(
        "email_relay.Message",
        data={"subject": "Low Priority", "to": ["low@example.com"]},
        status=Status.QUEUED,
        priority=Priority.LOW,
    )
    medium_priority_deferred = baker.make(
        "email_relay.Message",
        data={
            "subject": "Medium Priority, Deferred",
            "to": ["medium+deferred@example.com"],
        },
        status=Status.DEFERRED,
        priority=Priority.MEDIUM,
    )

    send_all()

    assert len(mailoutbox) == 3
    assert Message.objects.sent().count() == 3

    high_priority.refresh_from_db()
    low_priority.refresh_from_db()
    medium_priority_deferred.refresh_from_db()

    assert high_priority.status == Status.SENT
    assert low_priority.status == Status.SENT
    assert medium_priority_deferred.status == Status.SENT

    assert "sent 3 emails, deferred 0 emails, failed 0 emails" in caplog.text


@override_settings(DJANGO_EMAIL_RELAY={"EMAIL_MAX_BATCH": 2})
def test_send_all_respects_max_batch(mailoutbox, caplog):
    baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
        _quantity=5,
    )

    send_all()

    assert len(mailoutbox) == 2
    assert Message.objects.sent().count() == 2
    assert Message.objects.queued().count() == 3

    assert "sent 2 emails, deferred 0 emails, failed 0 emails" in caplog.text


@override_settings(DJANGO_EMAIL_RELAY={"EMAIL_THROTTLE": 0.01})
def test_send_all_respects_throttle(mailoutbox, caplog):
    baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 1
    assert Message.objects.sent().count() == 1
    assert "throttling enabled, sleeping for 0.01 seconds" in caplog.text
    assert "sent 1 emails, deferred 0 emails, failed 0 emails" in caplog.text


def test_send_all_sends_email_multi_alternatives(mailoutbox, caplog):
    email = EmailMultiAlternatives(
        subject="HTML Test",
        body="Text Body",
        from_email="html@example.com",
        to=["recipient@example.com"],
    )
    email.attach_alternative("<p>HTML Body</p>", "text/html")

    message = baker.make("email_relay.Message", status=Status.QUEUED)
    message.email = email
    message.save()

    send_all()

    assert len(mailoutbox) == 1

    sent_email = mailoutbox[0]

    assert sent_email.subject == "HTML Test"
    assert sent_email.body == "Text Body"
    assert sent_email.alternatives == [("<p>HTML Body</p>", "text/html")]

    message.refresh_from_db()

    assert message.status == Status.SENT
    assert f"sent message {message.id}" in caplog.text
    assert "sent 1 emails, deferred 0 emails, failed 0 emails" in caplog.text


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_defer_on_smtp_error(mock_send, mailoutbox, caplog):
    mock_send.side_effect = smtplib.SMTPSenderRefused(
        550, b"Test SMTP Error", "sender@example.com"
    )
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.DEFERRED
    assert queued.retry_count == 1
    assert "Test SMTP Error" in queued.log
    assert f"deferring message {queued.id} due to" in caplog.text
    assert "sent 0 emails, deferred 1 emails, failed 0 emails" in caplog.text


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_defer_on_os_error(mock_send, mailoutbox, caplog):
    mock_send.side_effect = OSError("Test Network Error")
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.DEFERRED
    assert queued.retry_count == 1
    assert "Test Network Error" in queued.log
    assert f"deferring message {queued.id} due to" in caplog.text
    assert "sent 0 emails, deferred 1 emails, failed 0 emails" in caplog.text


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_fail_after_max_retries(mock_send, mailoutbox, caplog):
    mock_send.side_effect = smtplib.SMTPSenderRefused(
        550, b"Test SMTP Error", "sender@example.com"
    )
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        retry_count=2,
        status=Status.DEFERRED,
    )

    with override_settings(DJANGO_EMAIL_RELAY={"EMAIL_MAX_RETRIES": 2}):
        send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.FAILED
    assert queued.retry_count == 2
    assert "Test SMTP Error" in queued.log
    assert f"max retries reached, marking message {queued.id} as failed" in caplog.text
    assert "sent 0 emails, deferred 0 emails, failed 1 emails" in caplog.text


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_throttles_after_max_retries_failure(send, mailoutbox, caplog):
    send.side_effect = smtplib.SMTPSenderRefused(
        550, b"Test SMTP Error", "sender@example.com"
    )
    baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        retry_count=2,
        status=Status.DEFERRED,
    )

    with (
        override_settings(
            DJANGO_EMAIL_RELAY={"EMAIL_MAX_RETRIES": 2, "EMAIL_THROTTLE": 0.01}
        ),
        mock.patch("email_relay.relay.time.sleep") as sleep,
    ):
        send_all()

    sleep.assert_called_once_with(0.01)


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_fail_on_value_error(mock_send, mailoutbox, caplog):
    mock_send.side_effect = ValueError("Test Value Error")
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.FAILED
    assert queued.retry_count == 0
    assert "Test Value Error" in queued.log
    assert (
        f"unexpected error processing message {queued.id}, marking as failed"
        in caplog.text
    )
    assert "sent 0 emails, deferred 0 emails, failed 1 emails" in caplog.text


@mock.patch("django.core.mail.message.EmailMultiAlternatives.send")
def test_send_all_fail_on_type_error(mock_send, mailoutbox, caplog):
    mock_send.side_effect = TypeError("Test Type Error")
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.FAILED
    assert queued.retry_count == 0
    assert "Test Type Error" in queued.log
    assert (
        f"unexpected error processing message {queued.id}, marking as failed"
        in caplog.text
    )
    assert "sent 0 emails, deferred 0 emails, failed 1 emails" in caplog.text


def test_send_all_continue_after_failure(mailoutbox, caplog):
    success = baker.make(
        "email_relay.Message",
        data={"subject": "Success", "to": ["ok@example.com"]},
        status=Status.QUEUED,
        priority=Priority.LOW,
    )
    fail = baker.make(
        "email_relay.Message",
        data={"subject": "Fail"},
        status=Status.QUEUED,
        priority=Priority.HIGH,
    )

    original_email_prop = Message.email.fget

    @property
    def mock_email_prop(self):
        if self.id == fail.id:
            # Simulate an error during email object creation/retrieval
            raise ValueError("Simulated property error")

        return original_email_prop(self)

    with mock.patch("email_relay.models.Message.email", mock_email_prop, create=True):
        send_all()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == "Success"

    success.refresh_from_db()
    fail.refresh_from_db()

    assert success.status == Status.SENT
    assert fail.status == Status.FAILED
    assert "Simulated property error" in fail.log

    assert f"sent message {success.id}" in caplog.text
    assert (
        f"unexpected error processing message {fail.id}, marking as failed"
        in caplog.text
    )
    assert "sent 1 emails, deferred 0 emails, failed 1 emails" in caplog.text


@mock.patch("email_relay.models.Message.email", new_callable=mock.PropertyMock)
def test_send_all_fail_message_no_email_object(mock_email, mailoutbox, caplog):
    mock_email.return_value = None
    queued = baker.make(
        "email_relay.Message",
        data={
            "subject": "Test Subject",
            "body": "Test Body",
            "from_email": "from@example.com",
            "to": ["to@example.com"],
        },
        status=Status.QUEUED,
    )

    send_all()

    assert len(mailoutbox) == 0

    queued.refresh_from_db()

    assert queued.status == Status.FAILED

    error_msg = f"Message {queued.id} has no email object"

    assert error_msg in queued.log
    assert error_msg in caplog.text
    assert "sent 0 emails, deferred 0 emails, failed 1 emails" in caplog.text


def test_send_all_fails_incomplete_stored_message_before_smtp(
    mailoutbox, caplog, create_stored_message
):
    queued = create_stored_message()
    queued.attachments.all().delete()

    send_all()

    queued.refresh_from_db()
    assert len(mailoutbox) == 0
    assert queued.status == Status.FAILED
    assert queued.retry_count == 0
    assert "does not match attachment rows" in queued.log
    assert f"invalid stored attachments for message {queued.id}" in caplog.text


def test_send_all_sends_stored_attachment(mailoutbox, caplog, create_stored_message):
    queued = create_stored_message()

    send_all()

    queued.refresh_from_db()
    assert queued.status == Status.SENT
    assert len(mailoutbox) == 1
    assert mailoutbox[0].attachments[0][1] == b"stored payload"
    assert "sent 1 emails, deferred 0 emails, failed 0 emails" in caplog.text


def test_send_all_retries_database_batch_error(mailoutbox, caplog):
    with (
        mock.patch(
            "email_relay.models.MessageManager.get_message_batch",
            side_effect=OperationalError("connection lost"),
        ),
        mock.patch("email_relay.relay.close_old_connections") as close_connections,
    ):
        send_all()

    close_connections.assert_called_once_with()
    assert len(mailoutbox) == 0
    assert "database error loading message batch" in caplog.text


@pytest.mark.parametrize("error_type", [InterfaceError, OperationalError])
def test_send_all_retries_attachment_query_error(
    error_type, mailoutbox, caplog, create_stored_message
):
    stored = create_stored_message()
    stored.priority = Priority.HIGH
    stored.save(update_fields=["priority"])
    following = baker.make(
        "email_relay.Message",
        data={"subject": "Following", "to": ["to@example.com"]},
        status=Status.QUEUED,
    )

    def fail_attachment_query(execute, sql, params, many, context):
        if MessageAttachment._meta.db_table in sql:
            raise error_type("connection lost")
        return execute(sql, params, many, context)

    with (
        connections[EMAIL_RELAY_DATABASE_ALIAS].execute_wrapper(fail_attachment_query),
        mock.patch("email_relay.relay.close_old_connections") as close_connections,
    ):
        send_all()

    close_connections.assert_called_once_with()
    for message in (stored, following):
        message.refresh_from_db()
        assert message.status == Status.QUEUED
        assert message.retry_count == 0
    assert len(mailoutbox) == 0
    assert "leaving it queued for retry" in caplog.text


@mock.patch("email_relay.models.Message.mark_sent")
def test_send_all_does_not_count_rolled_back_send(mark_sent, mailoutbox, caplog):
    mark_sent.side_effect = OperationalError("commit failed")
    queued = baker.make(
        "email_relay.Message",
        data={"subject": "Retry", "to": ["to@example.com"]},
        status=Status.QUEUED,
    )

    with mock.patch("email_relay.relay.close_old_connections"):
        send_all()

    queued.refresh_from_db()
    assert len(mailoutbox) == 1
    assert queued.status == Status.QUEUED
    assert "sent 0 emails, deferred 0 emails, failed 0 emails" in caplog.text


def test_send_all_uses_the_configured_database_transaction(mailoutbox):
    queued = baker.make(
        "email_relay.Message",
        data={"subject": "Alias", "to": ["to@example.com"]},
        status=Status.QUEUED,
    )

    with mock.patch(
        "email_relay.relay.transaction.atomic", wraps=transaction.atomic
    ) as atomic:
        send_all()

    queued.refresh_from_db()
    assert len(mailoutbox) == 1
    assert queued.status == Status.SENT
    atomic.assert_called_once_with(using=EMAIL_RELAY_DATABASE_ALIAS)
