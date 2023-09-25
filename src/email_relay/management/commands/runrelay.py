from __future__ import annotations

import logging
import time

from django.core.management import BaseCommand

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
