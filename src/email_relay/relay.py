from __future__ import annotations

import logging
import smtplib
import time
from itertools import chain
from socket import error as socket_error

from django.core.mail import get_connection
from django.db import transaction

from email_relay.conf import app_settings
from email_relay.models import Message

logger = logging.getLogger(__name__)


def send_all():
    connection = get_connection(backend=app_settings.EMAIL_BACKEND)

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

    if app_settings.EMAIL_MAX_BATCH is not None:
        message_batch = message_batch[: app_settings.EMAIL_MAX_BATCH]

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
                    connection = get_connection(backend=app_settings.EMAIL_BACKEND)
                email = message.email
                if email is not None:
                    email.connection = connection
                    email.send()
                    message.mark_sent()
                    counts["sent"] += 1
                else:
                    msg = f"Message {message.id} has no email object"
                    message.fail(log=msg)
                    logger.warning(msg)
            except Exception as err:
                if isinstance(
                    err,
                    (
                        smtplib.SMTPAuthenticationError,
                        smtplib.SMTPDataError,
                        smtplib.SMTPRecipientsRefused,
                        smtplib.SMTPSenderRefused,
                        socket_error,
                    ),
                ):
                    message.defer(log=str(err))
                    if message.retry_count >= app_settings.EMAIL_MAX_RETRIES:
                        message.fail(log=str(err))
                    connection = None
                    counts["deferred"] += 1
                else:
                    raise err

        if (
            app_settings.EMAIL_MAX_DEFERRED is not None
            and counts["deferred"] >= app_settings.EMAIL_MAX_DEFERRED
        ):
            break

        if app_settings.EMAIL_THROTTLE > 0:
            time.sleep(app_settings.EMAIL_THROTTLE)
