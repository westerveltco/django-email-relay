from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from email.message import Message as MIMEMessage
from typing import Any

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives

from email_relay import __version__
from email_relay.attachments import AttachmentKind
from email_relay.attachments import PersistedAttachmentError
from email_relay.attachments import RelayAttachment
from email_relay.attachments import deserialize_legacy_attachments
from email_relay.attachments import mime_attachment_from_bytes
from email_relay.attachments import serialize_legacy_attachments


@dataclass(frozen=True)
class RelayEmailData:
    subject: str = ""
    body: str = ""
    from_email: str = ""
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: list[str] = field(default_factory=list)
    extra_headers: dict[str, str] = field(default_factory=dict)
    alternatives: list[tuple[str, str]] = field(default_factory=list)
    _email_relay_version: str = __version__

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_email_message(
        cls, email_message: EmailMessage | EmailMultiAlternatives
    ) -> RelayEmailData:
        return cls(
            subject=str(email_message.subject),
            body=str(email_message.body),
            from_email=email_message.from_email,
            to=email_message.to,
            cc=email_message.cc,
            bcc=email_message.bcc,
            reply_to=email_message.reply_to,
            extra_headers=email_message.extra_headers,
            alternatives=getattr(email_message, "alternatives", []),
        )


@dataclass(frozen=True)
class RelayEmail:
    envelope: RelayEmailData
    attachments: tuple[RelayAttachment, ...] = ()

    def to_email_message(self) -> EmailMultiAlternatives:
        prepared_attachments: list[RelayAttachment | MIMEMessage] = []
        for attachment in self.attachments:
            if "/" not in attachment.content_type:
                raise PersistedAttachmentError(
                    "Stored attachment has an invalid content type"
                )
            if attachment.kind == AttachmentKind.MIME:
                mime_part = mime_attachment_from_bytes(attachment.content)
                if mime_part.get_content_type() != attachment.content_type:
                    raise PersistedAttachmentError(
                        "Stored MIME attachment content type does not match its metadata"
                    )
                if mime_part.get_filename() != attachment.filename:
                    raise PersistedAttachmentError(
                        "Stored MIME attachment filename does not match its metadata"
                    )
                prepared_attachments.append(mime_part)
            else:
                prepared_attachments.append(attachment)

        email = EmailMultiAlternatives(
            subject=self.envelope.subject,
            body=self.envelope.body,
            from_email=self.envelope.from_email,
            to=self.envelope.to,
            cc=self.envelope.cc,
            bcc=self.envelope.bcc,
            reply_to=self.envelope.reply_to,
            headers=self.envelope.extra_headers,
        )

        for alternative in self.envelope.alternatives:
            email.attach_alternative(alternative[0], alternative[1])

        for prepared in prepared_attachments:
            if isinstance(prepared, RelayAttachment):
                email.attach(
                    filename=prepared.filename,
                    content=prepared.content,
                    mimetype=prepared.content_type,
                )
            else:
                email.attach(prepared)  # type: ignore[call-overload]

        return email


def relay_email_from_legacy_data(data: dict[str, Any]) -> RelayEmail:
    envelope_data = dict(data)
    attachment_data = envelope_data.pop("attachments", [])
    try:
        envelope = RelayEmailData(**envelope_data)
    except TypeError as exc:
        raise PersistedAttachmentError("Invalid legacy email envelope") from exc
    return RelayEmail(
        envelope=envelope,
        attachments=deserialize_legacy_attachments(attachment_data),
    )


def serialize_legacy_email(
    email_message: EmailMessage | EmailMultiAlternatives,
) -> dict[str, Any]:
    """Preserve the attachment format written by 0.6.x producers."""
    data = RelayEmailData.from_email_message(email_message).to_dict()
    version = data.pop("_email_relay_version")
    data["attachments"] = serialize_legacy_attachments(email_message)
    data["_email_relay_version"] = version
    return data
