from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from django.conf import settings
from django.core.checks import Error
from django.core.checks import register
from django.core.files.storage import storages

from email_relay.conf import app_settings

RELAY_CHECK_TAG = "email_relay_relay"
_relay_checks_enabled: ContextVar[bool] = ContextVar(
    "email_relay_checks_enabled", default=False
)


@contextmanager
def relay_check_context() -> Iterator[None]:
    """Enable relay-only deployment checks for an explicit relay entrypoint."""
    token = _relay_checks_enabled.set(True)
    try:
        yield
    finally:
        _relay_checks_enabled.reset(token)


@register(RELAY_CHECK_TAG, deploy=True)
def check_relay_configuration(app_configs: Any = None, **kwargs: Any) -> list[Error]:
    del app_configs, kwargs
    if not _relay_checks_enabled.get():
        return []

    errors: list[Error] = []
    database_alias = app_settings.DATABASE_ALIAS
    if database_alias not in settings.DATABASES:
        errors.append(
            Error(
                f"Relay database alias {database_alias!r} is not configured.",
                hint=(
                    "Add the alias to DATABASES or set "
                    "DJANGO_EMAIL_RELAY['DATABASE_ALIAS'] to an existing alias."
                ),
                id="email_relay.E001",
            )
        )

    storage_alias = app_settings.ATTACHMENT_STORAGE_ALIAS
    try:
        storages[storage_alias]
    except Exception as exc:
        errors.append(
            Error(
                f"Relay attachment storage alias {storage_alias!r} is invalid "
                f"({type(exc).__name__}).",
                hint=(
                    "Add a working shared storage backend at "
                    f"STORAGES[{storage_alias!r}]."
                ),
                id="email_relay.E002",
            )
        )

    return errors
