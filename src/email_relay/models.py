from __future__ import annotations

import datetime
import hashlib
import logging
import re
from itertools import chain

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.utils import timezone

from email_relay.attachment_storage import ATTACHMENT_STORAGE_PREFIX
from email_relay.attachment_storage import attachment_storage
from email_relay.attachment_storage import attachment_upload_to
from email_relay.attachment_storage import read_attachment_file
from email_relay.attachments import STORED_ATTACHMENTS_KEY
from email_relay.attachments import AttachmentKind
from email_relay.attachments import PersistedAttachmentError
from email_relay.attachments import RelayAttachment
from email_relay.attachments import StoredAttachmentMarker
from email_relay.conf import app_settings
from email_relay.conf import resolved_database_alias
from email_relay.email import RelayEmail
from email_relay.email import RelayEmailData
from email_relay.email import relay_email_from_legacy_data
from email_relay.email import serialize_legacy_email

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
        message_batch = list(
            chain(
                self.queued().prioritized(),  # type: ignore[attr-defined]
                self.deferred().prioritized(),  # type: ignore[attr-defined]
            )
        )
        logger.debug("found %s messages to send", len(message_batch))
        if app_settings.EMAIL_MAX_BATCH is not None:
            msg = f"max batch size is {app_settings.EMAIL_MAX_BATCH}"
            if len(message_batch) > app_settings.EMAIL_MAX_BATCH:
                msg += ", truncating"
            logger.debug(msg)
            message_batch = message_batch[: app_settings.EMAIL_MAX_BATCH]
        return message_batch

    def get_message_for_sending(self, message_id: int) -> Message:
        return (
            self.filter(
                id=message_id,
                status__in=(Status.QUEUED, Status.DEFERRED),
            )
            .select_for_update(skip_locked=True)
            .get()
        )

    def messages_available_to_send(self) -> bool:
        return self.queued().exists() or self.deferred().exists()  # type: ignore[attr-defined]

    def delete_all_sent_messages(self) -> int:
        return self.sent().delete()[0]  # type: ignore[attr-defined]

    def delete_messages_sent_before(self, dt: datetime.datetime) -> int:
        return self.sent_before(dt).delete()[0]  # type: ignore[attr-defined]


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
        self.save()

    def defer(self, log: str = ""):
        self.status = Status.DEFERRED
        self.log = log
        self.retry_count += 1
        self.save()

    def fail(self, log: str = ""):
        self.status = Status.FAILED
        self.log = log
        self.save()

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
            return relay_email_from_legacy_data(data).to_email_message()

        if "attachments" in data:
            raise PersistedAttachmentError(
                "Message contains both legacy and stored attachments"
            )

        marker = StoredAttachmentMarker.from_value(data[STORED_ATTACHMENTS_KEY])
        database_alias = self._state.db or resolved_database_alias()
        rows = list(
            MessageAttachment.objects.using(database_alias)  # type: ignore[misc]  # django-stubs cannot resolve the later model here.
            .filter(message=self)
            .order_by("position")
        )
        if len(rows) != marker.count:
            raise PersistedAttachmentError(
                "Stored attachment count does not match attachment rows"
            )
        if [row.position for row in rows] != list(range(marker.count)):
            raise PersistedAttachmentError(
                "Stored attachment positions must be contiguous"
            )

        attachments: list[RelayAttachment] = []
        for row in rows:
            if not re.fullmatch(r"[0-9a-f]{64}", row.sha256):
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} has an invalid checksum"
                )
            try:
                kind = AttachmentKind(row.kind)
            except ValueError as exc:
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} has an unknown kind"
                ) from exc
            if not row.content_type:
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} has no content type"
                )
            if not isinstance(row.file.name, str) or not row.file.name.startswith(
                ATTACHMENT_STORAGE_PREFIX
            ):
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} is outside the package storage prefix"
                )

            content = read_attachment_file(row)
            if len(content) != row.size:
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} size does not match its metadata"
                )
            if hashlib.sha256(content).hexdigest() != row.sha256:
                raise PersistedAttachmentError(
                    f"Stored attachment {row.pk} checksum does not match its metadata"
                )
            attachments.append(
                RelayAttachment(
                    kind=kind,
                    filename=row.filename,
                    content_type=row.content_type,
                    content=content,
                )
            )

        envelope_data = dict(data)
        del envelope_data[STORED_ATTACHMENTS_KEY]
        try:
            envelope = RelayEmailData(**envelope_data)
        except TypeError as exc:
            raise PersistedAttachmentError("Invalid stored email envelope") from exc
        return RelayEmail(
            envelope=envelope, attachments=tuple(attachments)
        ).to_email_message()

    @email.setter
    def email(self, email_message: EmailMessage | EmailMultiAlternatives) -> None:
        self.data = serialize_legacy_email(email_message)


_MessageAttachmentManager = models.Manager["MessageAttachment"]


class MessageAttachment(models.Model):
    message_id: int

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    position = models.PositiveIntegerField()
    kind = models.CharField(
        max_length=16,
        choices=[
            (AttachmentKind.BYTES.value, "Bytes"),
            (AttachmentKind.MIME.value, "MIME"),
        ],
    )
    filename = models.TextField(null=True, blank=True)  # noqa: DJ001
    content_type = models.TextField()
    file = models.FileField(
        max_length=500,
        storage=attachment_storage,
        upload_to=attachment_upload_to,
    )
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = _MessageAttachmentManager()

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
