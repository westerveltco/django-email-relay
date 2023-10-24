from __future__ import annotations

import logging
import smtplib
import time
from itertools import chain
from socket import error as socket_error

from django.conf import settings
from django.core.mail import get_connection
from django.db import transaction

from email_relay.conf import app_settings
from email_relay.models import Message

logger = logging.getLogger(__name__)


def send_all():
    logger.info("sending emails")

    counts = {
        "sent": 0,
        "deferred": 0,
    }

    message_batch = list(
        chain(
            Message.objects.queued().prioritized(),
            Message.objects.deferred().prioritized(),
        )
    )
    logger.debug(f"found {len(message_batch)} messages to send")

    if app_settings.EMAIL_MAX_BATCH is not None:
        msg = f"max batch size is {app_settings.EMAIL_MAX_BATCH}"
        if len(message_batch) > app_settings.EMAIL_MAX_BATCH:
            msg += ", truncating"
        logger.debug(msg)
        message_batch = message_batch[: app_settings.EMAIL_MAX_BATCH]

    connection = None

    for message in message_batch:
        with transaction.atomic():
            try:
                message = (
                    Message.objects.filter(id=message.id)
                    .select_for_update(skip_locked=True)
                    .get()
                )
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
                    logger.debug(f"sent message {message.id}")
                    message.mark_sent()
                    counts["sent"] += 1
                else:
                    msg = f"Message {message.id} has no email object"
                    message.fail(log=msg)
                    logger.warning(msg)
            except Exception as err:
                handled_exceptions = (
                    smtplib.SMTPAuthenticationError,
                    smtplib.SMTPDataError,
                    smtplib.SMTPRecipientsRefused,
                    smtplib.SMTPSenderRefused,
                    socket_error,
                )
                if isinstance(err, handled_exceptions):
                    logger.debug(f"deferring message {message.id} due to {err}")
                    message.defer(log=str(err))
                    if message.retry_count >= app_settings.EMAIL_MAX_RETRIES:
                        logger.warning(
                            f"max retries reached, marking message {message.id} as failed"
                        )
                        message.fail(log=str(err))
                    connection = None
                    counts["deferred"] += 1
                else:
                    raise err

        if (
            app_settings.EMAIL_MAX_DEFERRED is not None
            and counts["deferred"] >= app_settings.EMAIL_MAX_DEFERRED
        ):
            logger.debug(
                f"max deferred emails reached ({app_settings.EMAIL_MAX_DEFERRED}), stopping"
            )
            break

        if app_settings.EMAIL_THROTTLE > 0:
            logger.debug(
                f"throttling enabled, sleeping for {app_settings.EMAIL_THROTTLE} seconds"
            )
            time.sleep(app_settings.EMAIL_THROTTLE)

    logger.info(f"sent {counts['sent']} emails, deferred {counts['deferred']} emails")
