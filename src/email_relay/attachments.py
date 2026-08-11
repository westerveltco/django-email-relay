from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from email import policy
from email.message import Message as MIMEMessage
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.parser import BytesParser
from enum import Enum
from typing import Any

import django
from django.core.mail import EmailMessage

STORED_ATTACHMENTS_KEY = "_email_relay_attachments"
STORED_ATTACHMENTS_FORMAT = "stored-v1"


class AttachmentKind(str, Enum):
    BYTES = "bytes"
    MIME = "mime"


class PersistedAttachmentError(ValueError):
    """Stored attachment metadata or content is invalid."""


@dataclass(frozen=True)
class RelayAttachment:
    kind: AttachmentKind
    filename: str | None
    content_type: str
    content: bytes


@dataclass(frozen=True)
class StoredAttachmentMarker:
    count: int

    @classmethod
    def from_value(cls, value: Any) -> StoredAttachmentMarker:
        if not isinstance(value, dict) or set(value) != {"format", "count"}:
            raise PersistedAttachmentError("Invalid stored attachment marker")
        if value["format"] != STORED_ATTACHMENTS_FORMAT:
            raise PersistedAttachmentError(
                f"Unknown stored attachment format: {value['format']!r}"
            )
        count = value["count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise PersistedAttachmentError(
                "Stored attachment count must be nonnegative"
            )
        return cls(count=count)


def decode_legacy_content(content: str) -> bytes:
    """Preserve the unmarked 0.6 decoding rule.

    Base64-looking ASCII text remains ambiguous and is decoded as Base64. Non-ASCII
    text cannot be Base64, so it falls back to its UTF-8 bytes.
    """
    try:
        return base64.b64decode(content)
    except (binascii.Error, ValueError):
        return content.encode("utf-8")


def deserialize_legacy_attachments(value: Any) -> tuple[RelayAttachment, ...]:
    if not isinstance(value, list):
        raise PersistedAttachmentError("Legacy attachments must be a list")

    attachments: list[RelayAttachment] = []
    for item in value:
        if not isinstance(item, dict):
            raise PersistedAttachmentError("Legacy attachment entries must be objects")
        filename = item.get("filename", "")
        content = item.get("content", "")
        content_type = item.get("mimetype", "")
        if filename is not None and not isinstance(filename, str):
            raise PersistedAttachmentError(
                "Legacy attachment filename must be text or null"
            )
        if not isinstance(content, str):
            raise PersistedAttachmentError("Legacy attachment content must be text")
        if not isinstance(content_type, str):
            raise PersistedAttachmentError("Legacy attachment MIME type must be text")
        attachments.append(
            RelayAttachment(
                kind=AttachmentKind.BYTES,
                filename=filename,
                content_type=content_type,
                content=decode_legacy_content(content),
            )
        )
    return tuple(attachments)


def serialize_legacy_attachments(email_message: EmailMessage) -> list[dict[str, Any]]:
    """Preserve the attachment format written by 0.6.x producers."""
    attachments: list[dict[str, Any]] = []
    for attachment in email_message.attachments:
        if isinstance(attachment, MIMEBase):
            payload = attachment.get_payload(decode=True)
            if not isinstance(payload, bytes):
                raise TypeError("Payload must be bytes for base64 encoding")
            attachments.append(
                {
                    "filename": attachment.get_filename(failobj="filename_not_found"),
                    "content": base64.b64encode(payload).decode(),
                    "mimetype": attachment.get_content_type(),
                }
            )
            continue

        content = attachment[1]
        if isinstance(content, bytes):
            serialized_content = base64.b64encode(content).decode("utf-8")
        else:
            serialized_content = content
        attachments.append(
            {
                "filename": attachment[0],
                "content": serialized_content,
                "mimetype": attachment[2],
            }
        )
    return attachments


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
