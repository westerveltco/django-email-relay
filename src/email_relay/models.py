from __future__ import annotations

import datetime
import logging
from itertools import chain

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db import transaction
from django.utils import timezone

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
RETENTION_DELETE_BATCH_SIZE = 1000


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
        queued = self.queued().prioritized()  # type: ignore[attr-defined]
        deferred = self.deferred().prioritized()  # type: ignore[attr-defined]
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
            self.filter(
                id=message_id,
                status__in=(Status.QUEUED, Status.DEFERRED),
            )
            .select_for_update(skip_locked=True)
            .get()
        )

    def messages_available_to_send(self) -> bool:
        return self.queued().exists() or self.deferred().exists()  # type: ignore[attr-defined]

    def _delete_messages(self, queryset: models.QuerySet[Message]) -> int:
        deleted_messages = 0
        while message_ids := list(
            queryset.order_by().values_list("pk", flat=True)[
                :RETENTION_DELETE_BATCH_SIZE
            ]
        ):
            with transaction.atomic(using=self.db):
                (
                    MessageAttachment.objects.using(self.db)  # type: ignore[misc]
                    .filter(message_id__in=message_ids)
                    .only("pk")
                    .delete()
                )
                _, deleted_by_model = queryset.filter(pk__in=message_ids).delete()
            batch_count = deleted_by_model.get(queryset.model._meta.label, 0)
            deleted_messages += batch_count
            if batch_count == 0:
                break
        return deleted_messages

    def delete_all_sent_messages(self) -> int:
        return self._delete_messages(self.sent())  # type: ignore[attr-defined]

    def delete_messages_sent_before(self, dt: datetime.datetime) -> int:
        return self._delete_messages(self.sent_before(dt))  # type: ignore[attr-defined]


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

            content = bytes(row.content)
            if len(content) != row.size:
                logger.warning(
                    "stored attachment %s size metadata is %s, actual size is %s",
                    row.pk,
                    row.size,
                    len(content),
                    extra={"attachment_id": row.pk, "message_id": self.pk},
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
    content = models.BinaryField()
    size = models.PositiveBigIntegerField()
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
