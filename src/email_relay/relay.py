from __future__ import annotations

import logging
import smtplib
import time

from django.conf import settings
from django.core.mail import get_connection
from django.db import transaction

from email_relay.conf import app_settings
from email_relay.models import Message

logger = logging.getLogger(__name__)


def send_all():
    logger.info("sending emails")

    counts = {
        "deferred": 0,
        "failed": 0,
        "sent": 0,
    }

    message_batch = Message.objects.get_message_batch()

    connection = None

    for message in message_batch:
        with transaction.atomic():
            try:
                message = Message.objects.get_message_for_sending(message.id)
            except Message.DoesNotExist:
                continue
            try:
                if connection is None:
                    relay_email_backend = getattr(
                        settings,
                        "EMAIL_BACKEND",
                        "django.core.mail.backends.smtp.EmailBackend",
                    )
                    connection = get_connection(backend=relay_email_backend)
                email = message.email
                if email is not None:
                    email.connection = connection
                    email.send()
                    logger.debug("sent message %s", message.id)
                    message.mark_sent()
                    counts["sent"] += 1
                else:
                    msg = f"Message {message.id} has no email object"
                    message.fail(log=msg)
                    counts["failed"] += 1
                    logger.warning(msg)
            except (
                smtplib.SMTPAuthenticationError,
                smtplib.SMTPDataError,
                smtplib.SMTPRecipientsRefused,
                smtplib.SMTPSenderRefused,
                OSError,
            ) as err:
                if (
                    app_settings.EMAIL_MAX_RETRIES is not None
                    and message.retry_count >= app_settings.EMAIL_MAX_RETRIES
                ):
                    logger.warning(
                        "max retries reached, marking message %s as failed", message.id
                    )
                    message.fail(log=str(err))
                    connection = None
                    counts["failed"] += 1
                    continue

                logger.debug(
                    "deferring message %s due to %s", message.id, err, exc_info=True
                )
                message.defer(log=str(err))
                connection = None
                counts["deferred"] += 1
            except Exception as err:
                logger.exception(
                    "unexpected error processing message %s, marking as failed.",
                    message.id,
                )
                message.fail(log=str(err))
                connection = None
                counts["failed"] += 1

        if (
            app_settings.EMAIL_MAX_DEFERRED is not None
            and counts["deferred"] >= app_settings.EMAIL_MAX_DEFERRED
        ):
            logger.debug(
                "max deferred emails reached (%s), stopping",
                app_settings.EMAIL_MAX_DEFERRED,
            )
            break

        if app_settings.EMAIL_THROTTLE > 0:
            logger.debug(
                "throttling enabled, sleeping for %s seconds",
                app_settings.EMAIL_THROTTLE,
            )
            time.sleep(app_settings.EMAIL_THROTTLE)

    logger.info(
        "sent %s emails, deferred %s emails, failed %s emails",
        counts["sent"],
        counts["deferred"],
        counts["failed"],
    )
