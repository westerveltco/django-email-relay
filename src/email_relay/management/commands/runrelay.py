from __future__ import annotations

import datetime
import logging
import time

from django.core.management import BaseCommand
from django.utils import timezone

from email_relay.conf import app_settings
from email_relay.models import Message
from email_relay.relay import send_all

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options) -> None:
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
            self.ping_healthcheck()

    def delete_old_messages(self) -> None:
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

    def ping_healthcheck(self) -> None:
        if app_settings.RELAY_HEALTHCHECK_URL is not None:
            if requests is None:
                logger.warning(
                    "Healthcheck URL configured but requests is not installed. "
                    "Please install requests to use the healthcheck feature."
                )
                return

            response = requests.request(
                method=app_settings.RELAY_HEALTHCHECK_METHOD,
                url=app_settings.RELAY_HEALTHCHECK_URL,
                timeout=app_settings.RELAY_HEALTHCHECK_TIMEOUT,
            )

            if response.status_code == app_settings.RELAY_HEALTHCHECK_STATUS_CODE:
                logger.debug("healthcheck ping successful")
            else:
                logger.warning(
                    f"healthcheck failed, got {response.status_code}, expected {app_settings.RELAY_HEALTHCHECK_STATUS_CODE}"
                )
