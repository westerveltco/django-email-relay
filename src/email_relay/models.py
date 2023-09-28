from __future__ import annotations

import datetime
from email.mime.base import MIMEBase

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.utils import timezone


class Priority(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"


class Status(models.IntegerChoices):
    QUEUED = 1, "Queued"
    DEFERRED = 2, "Deferred"
    FAILED = 3, "Failed"
    SENT = 4, "Sent"


class MessageQuerySet(models.QuerySet):
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


class Message(models.Model):
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

    objects = MessageQuerySet.as_manager()

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
        update_fields = kwargs.get("update_fields", None)
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
    def email(self) -> EmailMessage | None:
        data = self.data
        if not data:
            return None

        email = EmailMultiAlternatives(
            subject=data.get("subject", ""),
            body=data.get("message"),
            from_email=data.get("from_email"),
            to=data.get("recipient_list"),
        )

        html_message = data.get("html_message", None)
        if html_message:
            email.attach_alternative(html_message, "text/html")

        for attachment in data.get("attachments", []):
            if isinstance(attachment, dict):
                email.attach(**attachment)
            else:
                email.attach(*attachment)

        return email

    @email.setter
    def email(self, email_message: EmailMessage) -> None:
        self.data = {
            "subject": email_message.subject,
            "message": email_message.body,
            "from_email": email_message.from_email,
            "recipient_list": email_message.to,
            "html_message": next(
                (
                    alternative[0]
                    for alternative in getattr(email_message, "alternatives", [])
                    if alternative[1] == "text/html"
                ),
                None,
            ),
            "attachments": [
                {
                    "filename": attachment[0],
                    "content": attachment[1],
                    "mimetype": attachment[2],
                }
                if not isinstance(attachment, MIMEBase)
                else attachment
                for attachment in email_message.attachments
            ],
        }
