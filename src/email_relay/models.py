from __future__ import annotations

import datetime
import logging
from email.message import Message as MIMEMessage
from itertools import chain
from typing import Any

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.utils import timezone

from email_relay.attachments import STORED_ATTACHMENTS_KEY
from email_relay.attachments import PersistedAttachmentError
from email_relay.attachments import mime_attachment_from_bytes
from email_relay.attachments import normalize_attachment_content_type
from email_relay.attachments import normalize_attachment_filename
from email_relay.attachments import parse_stored_attachment_marker
from email_relay.attachments import validate_attachment_filename
from email_relay.conf import app_settings
from email_relay.conf import resolved_database_alias
from email_relay.email import RelayEmailData

logger = logging.getLogger(__name__)


class Priority(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"


class Status(models.IntegerChoices):
    QUEUED = 1, "Queued"
    DEFERRED = 2, "Deferred"
    FAILED = 3, "Failed"
    SENT = 4, "Sent"


class MessageManager(models.Manager["Message"]):
    def get_message_batch(self) -> list[Message]:
        messages = self.using(resolved_database_alias())
        queued = messages.queued().prioritized()  # type: ignore[attr-defined]
        deferred = messages.deferred().prioritized()  # type: ignore[attr-defined]
        if app_settings.EMAIL_MAX_BATCH is None:
            message_batch = list(chain(queued, deferred))
        else:
            limit = app_settings.EMAIL_MAX_BATCH
            queued_batch = list(queued[:limit])
            deferred_batch = list(deferred[: limit - len(queued_batch)])
            message_batch = queued_batch + deferred_batch
            logger.debug("max batch size is %s", limit)
        logger.debug("found %s messages to send", len(message_batch))
        return message_batch

    def get_message_for_sending(self, message_id: int) -> Message:
        return (
            self.using(resolved_database_alias())
            .filter(
                id=message_id,
                status__in=(Status.QUEUED, Status.DEFERRED),
            )
            .select_for_update(skip_locked=True)
            .get()
        )

    def messages_available_to_send(self) -> bool:
        messages = self.using(resolved_database_alias())
        return messages.queued().exists() or messages.deferred().exists()  # type: ignore[attr-defined]

    def delete_all_sent_messages(self) -> int:
        messages = self.using(resolved_database_alias())
        _, deleted_by_model = messages.sent().only("pk").delete()  # type: ignore[attr-defined]
        return deleted_by_model.get(self.model._meta.label, 0)

    def delete_messages_sent_before(self, dt: datetime.datetime) -> int:
        messages = self.using(resolved_database_alias())
        _, deleted_by_model = messages.sent_before(dt).only("pk").delete()  # type: ignore[attr-defined]
        return deleted_by_model.get(self.model._meta.label, 0)


class MessageQuerySet(models.QuerySet["Message"]):
    def prioritized(self):
        return self.order_by("-priority", "created_at")

    def high_priority(self):
        return self.filter(priority=Priority.HIGH)

    def medium_priority(self):
        return self.filter(priority=Priority.MEDIUM)

    def low_priority(self):
        return self.filter(priority=Priority.LOW)

    def queued(self):
        return self.filter(status=Status.QUEUED)

    def deferred(self):
        return self.filter(status=Status.DEFERRED)

    def failed(self):
        return self.filter(status=Status.FAILED)

    def sent(self):
        return self.filter(status=Status.SENT)

    def sent_before(self, dt: datetime.datetime):
        return self.sent().filter(sent_at__lte=dt)


# This is a workaround to make `mypy` happy
_MessageManager = MessageManager.from_queryset(MessageQuerySet)


class Message(models.Model):
    id: int
    data = models.JSONField()
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices, default=Priority.LOW
    )
    status = models.PositiveSmallIntegerField(
        choices=Status.choices, default=Status.QUEUED
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    log = models.TextField(
        blank=True, help_text="Most recent log message from the email backend, if any."
    )

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    objects = _MessageManager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        try:
            return f'{self.created_at} "{self.data["subject"]}" to {", ".join(self.data["to"])}'
        except Exception:
            return f"{self.created_at} <invalid message>"

    def save(self, *args, **kwargs):
        # Overriding the save method in order to make sure that
        # modified field is updated even if it is not given as
        # a parameter to the update field argument.
        update_fields = kwargs.get("update_fields")
        if update_fields:
            kwargs["update_fields"] = set(update_fields).union({"updated_at"})

        super().save(*args, **kwargs)

    def mark_sent(self):
        self.status = Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])

    def defer(self, log: str = ""):
        self.status = Status.DEFERRED
        self.log = log
        self.retry_count += 1
        self.save(update_fields=["status", "log", "retry_count"])

    def fail(self, log: str = ""):
        self.status = Status.FAILED
        self.log = log
        self.save(update_fields=["status", "log"])

    @property
    def email(self) -> EmailMultiAlternatives | None:
        data = self.data
        if not data:
            return None

        if STORED_ATTACHMENTS_KEY not in data:
            logger.info(
                "reading legacy JSON attachments for message %s",
                self.pk,
                extra={
                    "attachment_format": "legacy-json",
                    "message_id": self.pk,
                },
            )
            return RelayEmailData(**data).to_email_message()

        if "attachments" in data:
            raise PersistedAttachmentError(
                "Message contains both legacy and stored attachments"
            )

        prepared_attachments = MessageAttachment.objects.load_for_email(
            message=self, marker=data[STORED_ATTACHMENTS_KEY]
        )

        envelope_data = dict(data)
        del envelope_data[STORED_ATTACHMENTS_KEY]
        try:
            email = RelayEmailData(**envelope_data).to_email_message()
        except TypeError as exc:
            raise PersistedAttachmentError("Invalid stored email envelope") from exc

        for attachment in prepared_attachments:
            if isinstance(attachment, tuple):
                email.attach(*attachment)
            else:
                email.attach(attachment)  # type: ignore[call-overload]
        return email

    @email.setter
    def email(self, email_message: EmailMessage | EmailMultiAlternatives) -> None:
        self.data = RelayEmailData.from_email_message(email_message).to_dict()


class MessageAttachmentManager(models.Manager["MessageAttachment"]):
    def load_for_email(
        self, *, message: Message, marker: Any
    ) -> list[tuple[str | None, bytes, str] | MIMEMessage]:
        expected_count = parse_stored_attachment_marker(marker)
        if message.pk is None:
            raise PersistedAttachmentError(
                "Message with stored attachments has not been saved"
            )

        database_alias = message._state.db or resolved_database_alias()
        rows = list(
            self.using(database_alias)
            .filter(message_id=message.pk)
            .order_by("position")
        )
        if len(rows) != expected_count:
            raise PersistedAttachmentError(
                f"Stored attachment count for message {message.pk} does not match "
                f"attachment rows: marker expects {expected_count}, found {len(rows)}"
            )
        positions = [row.position for row in rows]
        if positions != list(range(expected_count)):
            raise PersistedAttachmentError(
                f"Stored attachment positions for message {message.pk} must be "
                f"contiguous from 0, found {positions}"
            )

        attachments = []
        for row in rows:
            try:
                attachments.append(row.to_email_attachment())
            except PersistedAttachmentError as exc:
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk}: {exc}"
                ) from exc
        return attachments


class MessageAttachment(models.Model):
    class Kind(models.TextChoices):
        BYTES = "bytes", "Bytes"
        MIME = "mime", "MIME"

    message_id: int

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    position = models.PositiveIntegerField()
    kind = models.CharField(max_length=16, choices=Kind.choices)
    filename = models.TextField(null=True, blank=True)  # noqa: DJ001
    content_type = models.TextField()
    content = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = MessageAttachmentManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("message", "position"),
                name="email_relay_msgattach_pos_uniq",
            )
        ]

    def __str__(self) -> str:
        return (
            f"attachment {self.pk} for message {self.message_id} "
            f"at position {self.position}"
        )

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields:
            kwargs["update_fields"] = set(update_fields).union({"updated_at"})
        super().save(*args, **kwargs)

    def to_email_attachment(self) -> tuple[str | None, bytes, str] | MIMEMessage:
        content_type = normalize_attachment_content_type(self.content_type)
        content = bytes(self.content)

        if self.kind == self.Kind.BYTES:
            return validate_attachment_filename(self.filename), content, content_type

        if self.kind == self.Kind.MIME:
            mime_part = mime_attachment_from_bytes(content)
            if mime_part.get_content_type() != content_type:
                raise PersistedAttachmentError(
                    "MIME content type does not match its metadata"
                )
            mime_filename = normalize_attachment_filename(mime_part.get_filename())
            stored_filename = normalize_attachment_filename(self.filename)
            if mime_filename != stored_filename:
                raise PersistedAttachmentError(
                    "MIME filename does not match its metadata"
                )
            return mime_part

        raise PersistedAttachmentError(f"unknown kind {self.kind!r}")
