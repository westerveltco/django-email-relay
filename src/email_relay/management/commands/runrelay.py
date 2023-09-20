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
        while True:
            while (
                not Message.objects.queued().exists()
                and not Message.objects.deferred().exists()
            ):
                logger.debug(
                    f"sleeping for {app_settings.EMPTY_QUEUE_SLEEP} seconds before checking queue again"
                )
                time.sleep(app_settings.EMPTY_QUEUE_SLEEP)

            send_all()
