from __future__ import annotations

import datetime
import logging
import time

from django.core.management import BaseCommand
from django.utils import timezone

from email_relay.conf import app_settings
from email_relay.models import Message
from email_relay.relay import send_all

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("starting relay")
        while True:
            while (
                not Message.objects.queued().exists()
                and not Message.objects.deferred().exists()
            ):
                msg = "queue is empty"
                if app_settings.EMPTY_QUEUE_SLEEP > 0:
                    msg += f", sleeping for {app_settings.EMPTY_QUEUE_SLEEP} seconds before checking queue again"
                    time.sleep(app_settings.EMPTY_QUEUE_SLEEP)
                logger.debug(msg)

            send_all()
            self.delete_old_messages()

    def delete_old_messages(self):
        if app_settings.MESSAGES_RETENTION_SECONDS is not None:
            logger.debug("deleting old messages")
            if app_settings.MESSAGES_RETENTION_SECONDS == 0:
                deleted_messages = Message.objects.sent().delete()
            else:
                deleted_messages = Message.objects.sent_before(
                    timezone.now()
                    - datetime.timedelta(
                        seconds=app_settings.MESSAGES_RETENTION_SECONDS
                    )
                ).delete()
            logger.debug(f"deleted {deleted_messages[0]} messages")
