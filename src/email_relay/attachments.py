from __future__ import annotations

from email import policy
from email.message import Message as MIMEMessage
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.parser import BytesParser
from typing import Any

import django

STORED_ATTACHMENTS_KEY = "_email_relay_attachments"
STORED_ATTACHMENTS_FORMAT = "stored-v1"


class PersistedAttachmentError(ValueError):
    """Stored attachment metadata or content is invalid."""


def parse_stored_attachment_marker(value: Any) -> int:
    if not isinstance(value, dict) or set(value) != {"format", "count"}:
        raise PersistedAttachmentError("Invalid stored attachment marker")
    if value["format"] != STORED_ATTACHMENTS_FORMAT:
        raise PersistedAttachmentError(
            f"Unknown stored attachment format: {value['format']!r}"
        )
    count = value["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise PersistedAttachmentError("Stored attachment count must be nonnegative")
    return count


def mime_attachment_from_bytes(content: bytes) -> MIMEMessage:
    """Rebuild a complete serialized MIME entity for the running Django API."""
    if django.VERSION >= (6, 0):
        mime_part = BytesParser(
            _class=MIMEPart,  # type: ignore[arg-type]  # Django 6 requires MIMEPart.
            policy=policy.default,
        ).parsebytes(content)
        if mime_part.defects or mime_part.get("Content-Type") is None:
            raise PersistedAttachmentError("Stored MIME attachment is malformed")
        if mime_part.get_content_maintype() == "multipart":
            raise PersistedAttachmentError("Multipart MIME attachments are unsupported")
        return mime_part

    parsed = BytesParser(policy=policy.compat32).parsebytes(content)
    if parsed.defects or parsed.get("Content-Type") is None:
        raise PersistedAttachmentError("Stored MIME attachment is malformed")
    if parsed.get_content_maintype() == "multipart":
        raise PersistedAttachmentError("Multipart MIME attachments are unsupported")

    content_type = parsed.get_content_type()
    main_type, sub_type = content_type.split("/", 1)
    mime_base = MIMEBase(main_type, sub_type)
    for name in list(mime_base.keys()):
        del mime_base[name]
    for name, value in parsed.raw_items():
        mime_base[name] = value
    mime_base.set_payload(parsed.get_payload())
    return mime_base
