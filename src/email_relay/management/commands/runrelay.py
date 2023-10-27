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
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, _loop_count: int | None = None, **options) -> None:
        # _loop_count is used to make testing a bit easier
        # it is not intended to be used in production
        loop_count = 0 if _loop_count is not None else None

        logger.info("starting relay")

        while True:
            if Message.objects.queued().exists() or Message.objects.deferred().exists():
                send_all()

            self.delete_old_messages()
            self.ping_healthcheck()

            msg = "loop complete"
            if app_settings.EMPTY_QUEUE_SLEEP > 0:
                msg += f", sleeping for {app_settings.EMPTY_QUEUE_SLEEP} seconds before next loop"
            logger.debug(msg)

            if _loop_count is not None and loop_count is not None:
                loop_count += 1
                if loop_count >= _loop_count:
                    break

            time.sleep(app_settings.EMPTY_QUEUE_SLEEP)

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

            logger.debug("pinging healthcheck")
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
