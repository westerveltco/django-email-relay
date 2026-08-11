from __future__ import annotations

import logging
import smtplib
import time

from django.conf import settings
from django.core.mail import get_connection
from django.db import InterfaceError
from django.db import OperationalError
from django.db import close_old_connections
from django.db import transaction

from email_relay.attachments import PersistedAttachmentError
from email_relay.conf import app_settings
from email_relay.conf import resolved_database_alias
from email_relay.models import Message

logger = logging.getLogger(__name__)


def send_all():
    logger.info("sending emails")

    counts = {
        "deferred": 0,
        "failed": 0,
        "sent": 0,
    }

    database_alias = resolved_database_alias()
    try:
        message_batch = Message.objects.get_message_batch()
    except (InterfaceError, OperationalError) as err:
        close_old_connections()
        logger.warning("database error loading message batch: %s", err)
        message_batch = []

    connection = None

    for message in message_batch:
        outcome: str | None = None
        skip_post_processing = False
        try:
            with transaction.atomic(using=database_alias):
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
                        outcome = "sent"
                    else:
                        msg = f"Message {message.id} has no email object"
                        message.fail(log=msg)
                        outcome = "failed"
                        logger.warning(msg)
                except (InterfaceError, OperationalError):
                    raise
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
                            "max retries reached, marking message %s as failed",
                            message.id,
                        )
                        message.fail(log=str(err))
                        connection = None
                        outcome = "failed"
                        skip_post_processing = True
                    else:
                        logger.debug(
                            "deferring message %s due to %s",
                            message.id,
                            err,
                            exc_info=True,
                        )
                        message.defer(log=str(err))
                        connection = None
                        outcome = "deferred"
                except PersistedAttachmentError as err:
                    logger.warning(
                        "invalid stored attachments for message %s, marking as failed: %s",
                        message.id,
                        err,
                    )
                    message.fail(log=str(err))
                    connection = None
                    outcome = "failed"
                except Exception as err:
                    logger.exception(
                        "unexpected error processing message %s, marking as failed.",
                        message.id,
                    )
                    message.fail(log=str(err))
                    connection = None
                    outcome = "failed"
        except (InterfaceError, OperationalError) as err:
            close_old_connections()
            logger.warning(
                "database error processing message %s; leaving it queued for retry: %s",
                message.id,
                err,
            )
            connection = None
            break

        if outcome is not None:
            counts[outcome] += 1
        if skip_post_processing:
            continue

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
