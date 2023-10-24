from __future__ import annotations

from collections.abc import Sequence

from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend

from email_relay.conf import app_settings
from email_relay.models import Message


class RelayDatabaseEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        messages = Message.objects.bulk_create(
            [Message(email=email) for email in email_messages],
            app_settings.MESSAGES_BATCH_SIZE,
        )
        return len(messages)
