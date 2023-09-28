from __future__ import annotations

import datetime

import pytest
from django.utils import timezone
from model_bakery import baker

from email_relay.models import Message
from email_relay.models import Priority
from email_relay.models import Status


@pytest.mark.django_db(databases=["default", "email_relay_db"])
def test_message():
    baker.make("email_relay.Message")
    assert Message.objects.all().count() == 1


@pytest.mark.django_db(databases=["default", "email_relay_db"])
class TestMessageQuerySet:
    @pytest.fixture
    def messages_with_priority(self):
        low = baker.make("email_relay.Message", priority=Priority.LOW)
        medium = baker.make("email_relay.Message", priority=Priority.MEDIUM)
        high = baker.make("email_relay.Message", priority=Priority.HIGH)
        return {
            "low": low,
            "medium": medium,
            "high": high,
        }

    @pytest.fixture
    def messages_with_status(self):
        queued = baker.make("email_relay.Message", status=Status.QUEUED)
        deferred = baker.make("email_relay.Message", status=Status.DEFERRED)
        failed = baker.make("email_relay.Message", status=Status.FAILED)
        sent = baker.make("email_relay.Message", status=Status.SENT)
        return {
            "queued": queued,
            "deferred": deferred,
            "failed": failed,
            "sent": sent,
        }

    def test_prioritized(self, messages_with_priority):
        queryset = Message.objects.prioritized()

        assert queryset.count() == 3
        assert queryset[0] == messages_with_priority["high"]
        assert queryset[1] == messages_with_priority["medium"]
        assert queryset[2] == messages_with_priority["low"]

    def test_high_priority(self, messages_with_priority):
        queryset = Message.objects.high_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["high"]

    def test_medium_priority(self, messages_with_priority):
        queryset = Message.objects.medium_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["medium"]

    def test_low_priority(self, messages_with_priority):
        queryset = Message.objects.low_priority()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_priority["low"]

    def test_queued(self, messages_with_status):
        queryset = Message.objects.queued()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["queued"]

    def test_deferred(self, messages_with_status):
        queryset = Message.objects.deferred()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["deferred"]

    def test_failed(self, messages_with_status):
        queryset = Message.objects.failed()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["failed"]

    def test_sent(self, messages_with_status):
        queryset = Message.objects.sent()

        assert queryset.count() == 1
        assert queryset[0] == messages_with_status["sent"]

    def test_sent_before(self):
        one_week = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now() - datetime.timedelta(days=7),
        )
        now = baker.make(
            "email_relay.Message",
            status=Status.SENT,
            sent_at=timezone.now(),
        )
        not_sent = baker.make(
            "email_relay.Message",
            status=Status.QUEUED,
            sent_at=None,
        )

        queryset = Message.objects.sent_before(
            timezone.now() - datetime.timedelta(days=1)
        )

        assert queryset.count() == 1
        assert one_week in queryset
        assert now not in queryset
        assert not_sent not in queryset
