from __future__ import annotations

import base64
import binascii
import re
from email import policy
from email.errors import HeaderParseError
from email.header import decode_header
from email.header import make_header
from email.headerregistry import HeaderRegistry
from email.message import Message as MIMEMessage
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.parser import BytesParser
from typing import Any
from typing import cast

import django

STORED_ATTACHMENTS_KEY = "_email_relay_attachments"
STORED_ATTACHMENTS_FORMAT = "stored-v1"
_MIME_TOKEN_PATTERN = re.compile(r"[!#$%&'+.^_`|~0-9A-Za-z-]+")
_HEADER_FOLD_PATTERN = re.compile(r"\r?\n[ \t]+")
_HEADER_REGISTRY = HeaderRegistry()
_SUPPORTED_TRANSFER_ENCODINGS = {
    "7bit",
    "8bit",
    "base64",
    "binary",
    "quoted-printable",
}


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


class _ParsedMIMEBase(MIMEBase):
    """Parser target accepted by Django versions before 6.0."""

    def __init__(self, *, policy=policy.compat32):
        MIMEMessage.__init__(self, policy=policy)


def _is_mime_token(value: str) -> bool:
    return _MIME_TOKEN_PATTERN.fullmatch(value) is not None


def normalize_attachment_content_type(value: str) -> str:
    """Validate and normalize a stored attachment content type."""
    parts = value.split("/")
    if len(parts) != 2 or not all(_is_mime_token(part) for part in parts):
        raise PersistedAttachmentError("invalid content type")
    return value.lower()


def _unfold_header(value: str) -> str:
    return _HEADER_FOLD_PATTERN.sub(" ", value)


def normalize_attachment_filename(value: str | None) -> str | None:
    """Normalize a MIME filename across the supported parser policies."""
    if not value:
        return None
    try:
        return str(make_header(decode_header(_unfold_header(value))))
    except (HeaderParseError, LookupError, UnicodeError, ValueError) as exc:
        raise PersistedAttachmentError("invalid filename") from exc


def _validate_mime_attachment(mime_part: MIMEMessage) -> None:
    content_type_headers = mime_part.get_all("Content-Type", [])
    if len(content_type_headers) != 1:
        raise PersistedAttachmentError("MIME attachment is malformed")
    if mime_part.get_content_maintype() == "multipart":
        raise PersistedAttachmentError("Multipart MIME attachments are unsupported")

    for part in mime_part.walk():
        if part.defects:
            raise PersistedAttachmentError("MIME attachment is malformed")

        content_type_headers = part.get_all("Content-Type", [])
        if len(content_type_headers) > 1:
            raise PersistedAttachmentError("MIME attachment is malformed")
        if content_type_headers:
            header = cast(
                Any,
                _HEADER_REGISTRY(
                    "Content-Type",
                    _unfold_header(str(content_type_headers[0])),
                ),
            )
            if (
                header.defects
                or not _is_mime_token(header.maintype)
                or not _is_mime_token(header.subtype)
            ):
                raise PersistedAttachmentError("MIME attachment is malformed")

        transfer_encodings = part.get_all("Content-Transfer-Encoding", [])
        if len(transfer_encodings) > 1:
            raise PersistedAttachmentError("MIME attachment is malformed")
        transfer_encoding = None
        if transfer_encodings:
            transfer_encoding = transfer_encodings[0].strip().lower()
            if (
                not _is_mime_token(transfer_encoding)
                or transfer_encoding not in _SUPPORTED_TRANSFER_ENCODINGS
            ):
                raise PersistedAttachmentError("MIME attachment is malformed")

        if part.is_multipart():
            continue

        payload = part.get_payload()
        if not isinstance(payload, str):
            raise PersistedAttachmentError("MIME attachment is malformed")

        if transfer_encoding in (None, "7bit", "quoted-printable"):
            try:
                payload.encode("ascii")
            except UnicodeEncodeError as exc:
                raise PersistedAttachmentError(
                    "MIME attachment has invalid transfer encoding"
                ) from exc

        if transfer_encoding == "base64":
            try:
                encoded = payload.encode("ascii")
                compact = encoded.translate(None, b" \t\r\n")
                decoded = base64.b64decode(compact, validate=True)
            except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
                raise PersistedAttachmentError(
                    "MIME attachment contains malformed Base64"
                ) from exc
            if base64.b64encode(decoded) != compact:
                raise PersistedAttachmentError(
                    "MIME attachment contains noncanonical Base64"
                )


def mime_attachment_from_bytes(content: bytes) -> MIMEMessage:
    """Rebuild a complete serialized MIME entity for the running Django API."""
    mime_part: MIMEMessage
    if django.VERSION >= (6, 0):
        mime_part = BytesParser(
            _class=MIMEPart,  # type: ignore[arg-type]  # Django 6 requires MIMEPart.
            policy=policy.default,
        ).parsebytes(content)
    else:
        mime_part = BytesParser(
            _class=_ParsedMIMEBase,
            policy=policy.compat32,
        ).parsebytes(content)

    _validate_mime_attachment(mime_part)
    return mime_part
