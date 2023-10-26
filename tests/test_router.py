from __future__ import annotations

import pytest

from email_relay.conf import app_settings
from email_relay.db import EmailDatabaseRouter


# Mock model with app_label "email_relay"
class MockModel:
    class _meta:
        app_label = "email_relay"


# Mock model with app_label "some_other_app"
class MockModelOther:
    class _meta:
        app_label = "some_other_app"


@pytest.fixture
def router():
    return EmailDatabaseRouter()


def test_db_for_read(router):
    assert router.db_for_read(MockModel) == app_settings.DATABASE_ALIAS
    assert router.db_for_read(MockModelOther) == "default"


def test_db_for_write(router):
    assert router.db_for_write(MockModel) == app_settings.DATABASE_ALIAS
    assert router.db_for_write(MockModelOther) == "default"


def test_allow_relation(router):
    assert router.allow_relation(MockModel, MockModel)


def test_allow_migrate(router):
    assert router.allow_migrate(app_settings.DATABASE_ALIAS, "email_relay")
