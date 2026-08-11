from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.storage import storages

from email_relay.attachments import AttachmentStorageError
from email_relay.conf import app_settings

ATTACHMENT_STORAGE_PREFIX = "email-relay/attachments/v1/"


class EmailRelayAttachmentStorage(Storage):
    """Delegate to the configured named storage without resolving it at import."""

    def deconstruct(self) -> tuple[str, tuple[()], dict[str, object]]:
        return (
            "email_relay.attachment_storage.EmailRelayAttachmentStorage",
            (),
            {},
        )

    @property
    def backend(self) -> Storage:
        return storages[app_settings.ATTACHMENT_STORAGE_ALIAS]

    def _open(self, name: str, mode: str = "rb") -> File:
        return self.backend.open(name, mode)

    def save(
        self, name: str | None, content: Any, max_length: int | None = None
    ) -> str:
        return self.backend.save(name, content, max_length=max_length)

    def _save(self, name: str, content: Any) -> str:
        return self.backend.save(name, content)

    def delete(self, name: str) -> None:
        return self.backend.delete(name)

    def exists(self, name: str) -> bool:
        return self.backend.exists(name)

    def listdir(self, path: str) -> tuple[list[str], list[str]]:
        return self.backend.listdir(path)

    def size(self, name: str) -> int:
        return self.backend.size(name)

    def url(self, name: str | None) -> str:
        return self.backend.url(name)

    def path(self, name: str) -> str:
        return self.backend.path(name)

    def get_accessed_time(self, name: str) -> datetime:
        return self.backend.get_accessed_time(name)

    def get_created_time(self, name: str) -> datetime:
        return self.backend.get_created_time(name)

    def get_modified_time(self, name: str) -> datetime:
        return self.backend.get_modified_time(name)


attachment_storage = EmailRelayAttachmentStorage()


def generate_attachment_key() -> str:
    identifier = uuid.uuid4().hex
    return f"{ATTACHMENT_STORAGE_PREFIX}{identifier[:2]}/{identifier}"


def attachment_upload_to(instance: Any, filename: str) -> str:
    del instance, filename
    return generate_attachment_key()


def read_attachment_file(attachment: Any) -> bytes:
    try:
        with attachment.file.open("rb") as stored_file:
            return stored_file.read()
    except Exception as exc:
        raise AttachmentStorageError(
            f"Could not read stored attachment {attachment.pk}"
        ) from exc
