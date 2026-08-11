from __future__ import annotations

from collections.abc import Sequence

from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend

from email_relay.conf import app_settings
from email_relay.models import Message
from email_relay.models import store_message_attachments


class RelayDatabaseEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        messages_to_create = []
        attachments_by_message = []
        for email_message in email_messages:
            message = Message(email=email_message)
            attachments_by_message.append(message.data.pop("attachments", []))
            messages_to_create.append(message)

        created_messages = Message.objects.bulk_create(
            messages_to_create, app_settings.MESSAGES_BATCH_SIZE
        )
        for message, attachments in zip(created_messages, attachments_by_message):
            store_message_attachments(message, attachments)

        return len(created_messages)
