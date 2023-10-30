from __future__ import annotations

import base64
import binascii
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from email.mime.base import MIMEBase

from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives


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
    attachments: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_email_message(self) -> EmailMultiAlternatives:
        email = EmailMultiAlternatives(
            subject=self.subject,
            body=self.body,
            from_email=self.from_email,
            to=self.to,
            cc=self.cc,
            bcc=self.bcc,
            reply_to=self.reply_to,
            headers=self.extra_headers,
        )

        for alternative in self.alternatives:
            email.attach_alternative(alternative[0], alternative[1])

        for attachment in self.attachments:
            content = attachment.get("content", "")
            try:
                # Attempt to decode the base64 string into bytes
                decoded_content = base64.b64decode(content)
            except binascii.Error:
                # Fallback to assuming it's plain text, encoded as bytes
                decoded_content = content.encode("utf-8")

            email.attach(
                filename=attachment.get("filename", ""),
                content=decoded_content,
                mimetype=attachment.get("mimetype", ""),
            )

        return email

    @classmethod
    def from_email_message(
        cls, email_message: EmailMessage | EmailMultiAlternatives
    ) -> RelayEmailData:
        attachments = []
        for attachment in email_message.attachments:
            if isinstance(attachment, MIMEBase):
                attachments.append(
                    {
                        "filename": attachment.get_filename(
                            failobj="filename_not_found"
                        ),
                        "content": base64.b64encode(
                            attachment.get_payload(decode=True)
                        ).decode(),
                        "mimetype": attachment.get_content_type(),
                    }
                )
            else:
                if isinstance(attachment[1], bytes):
                    content = base64.b64encode(attachment[1]).decode("utf-8")
                else:
                    content = attachment[1]

                attachments.append(
                    {
                        "filename": attachment[0],
                        "content": content,
                        "mimetype": attachment[2],
                    }
                )

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
            attachments=attachments,
        )
