from __future__ import annotations

import pytest
from model_bakery import baker

from email_relay.models import Message


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_message():
    baker.make("email_relay.Message")
    assert Message.objects.all().count() == 1
