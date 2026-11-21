import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from django.db import connections
from django.utils import timezone

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.identity.models import HumanUser
from chatballs.testing import TenantAPIClient
from chatballs.updates.check_in import check_in_if_due
from chatballs.updates.check_in_client import (
    DAILY_INTERVAL,
    RETRY_INTERVAL,
    CheckInResult,
    _build_request,
    _rate_limit_delay,
    _read_response,
    parse_announcements,
)
from chatballs.updates.check_in_state import (
    CheckInState,
    announcement_snapshot,
    finish_attempt,
    reserve_attempt,
    reset_for_independent_copy,
    still_allowed,
)

VERSION = "1.23.0"


@pytest.mark.django_db(transaction=True)
def test_only_one_database_connection_claims_a_due_check_in():
    start = Barrier(2, timeout=15)

    def claim():
        try:
            start.wait()
            return reserve_attempt(VERSION)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        attempts = [workers.submit(claim) for _ in range(2)]
        claimed = [attempt for future in attempts if (attempt := future.result()) is not None]

    assert len(claimed) == 1
    state = CheckInState.objects.get()
    assert state.installation_id == claimed[0].installation_id
    assert state.installation_id.version == 4
    assert still_allowed(claimed[0])
    assert reserve_attempt(VERSION) is None


@pytest.mark.django_db
def test_expired_reservation_can_be_recovered_and_rejects_old_result():
    first = reserve_attempt(VERSION)
    CheckInState.objects.update(next_attempt_at=timezone.now())
    second = reserve_attempt(VERSION)
    assert second.installation_id == first.installation_id
    assert second.id != first.id
    assert not still_allowed(first)
    assert not finish_attempt(first, CheckInResult(announcements=[]))


@pytest.mark.django_db
def test_success_replaces_snapshot_and_schedules_daily():
    attempt = reserve_attempt(VERSION)
    messages = [{"id": 42, "title": "Заголовок", "text": "Первый абзац.\n\nВторой.", "link": ""}]
    assert finish_attempt(attempt, CheckInResult(announcements=messages))
    snapshot = announcement_snapshot()
    assert snapshot["announcements"] == messages
    assert 0 < snapshot["expiresInMs"] <= 86_400_000
    state = CheckInState.objects.get()
    assert state.next_attempt_at - state.received_at == DAILY_INTERVAL
    CheckInState.objects.update(received_at=timezone.now() - DAILY_INTERVAL)
    assert announcement_snapshot()["announcements"] is None

    CheckInState.objects.update(next_attempt_at=timezone.now())
    assert finish_attempt(reserve_attempt(VERSION), CheckInResult(announcements=[]))
    assert announcement_snapshot()["announcements"] == []


@pytest.mark.django_db
@pytest.mark.parametrize("old_result", [
    CheckInResult(announcements=[]), CheckInResult(error="timeout", delay=RETRY_INTERVAL),
])
def test_old_result_cannot_reappear_after_disabling_and_enabling(old_result):
    attempt = reserve_attempt(VERSION)
    assert finish_attempt(attempt, CheckInResult(announcements=[]))
    assert announcement_snapshot()["announcements"] == []
    CheckInState.objects.update(next_attempt_at=timezone.now())
    in_flight = reserve_attempt(VERSION)
    InstanceSettings.objects.update(external_checks_enabled=False, external_checks_revision=1)
    assert not still_allowed(in_flight)
    assert announcement_snapshot() == {
        "enabled": False, "failed": False, "announcements": None, "expiresInMs": None,
    }
    assert reserve_attempt(VERSION) is None

    InstanceSettings.objects.update(external_checks_enabled=True, external_checks_revision=2)
    assert finish_attempt(in_flight, old_result)
    assert announcement_snapshot() == {
        "enabled": True, "failed": False, "announcements": None, "expiresInMs": None,
    }
    CheckInState.objects.update(next_attempt_at=timezone.now())
    assert reserve_attempt(VERSION).installation_id == attempt.installation_id


@pytest.mark.django_db
def test_rate_limit_keeps_prior_snapshot_and_persists_next_attempt():
    assert finish_attempt(reserve_attempt(VERSION), CheckInResult(announcements=[]))
    CheckInState.objects.update(next_attempt_at=timezone.now())
    before = timezone.now()
    wait = _rate_limit_delay("3600")
    assert finish_attempt(reserve_attempt(VERSION), CheckInResult(error="http_429", delay=wait))
    state = CheckInState.objects.get()
    assert state.next_attempt_at >= before + timedelta(hours=1)
    assert state.last_error == "http_429"
    assert reserve_attempt(VERSION) is None
    snapshot = announcement_snapshot()
    assert snapshot["announcements"] == []
    assert snapshot["failed"] is True
    assert _rate_limit_delay("Wed, 21 Oct 2015") == RETRY_INTERVAL


@pytest.mark.django_db
def test_copy_reset_assigns_a_new_uuid_and_drops_inherited_state():
    original = reserve_attempt(VERSION)
    assert finish_attempt(original, CheckInResult(announcements=[]))
    reset_for_independent_copy()
    copy = CheckInState.objects.get()
    assert copy.installation_id.version == 4
    assert copy.installation_id != original.installation_id
    assert copy.next_attempt_at is None
    assert copy.received_at is None
    assert copy.announcements == []
    assert reserve_attempt(VERSION) is None


@pytest.mark.django_db
def test_switch_can_be_saved_with_a_preexisting_local_address():
    row = InstanceSettings.load()
    row.public_host = "localhost"
    row.public_port = 5174
    row.public_scheme = "http"
    row.save()
    client = TenantAPIClient()
    admin = HumanUser.objects.create_user(email="check-in-settings@example.test", is_instance_admin=True)
    client.force_authenticate(admin)

    response = client.patch(
        "/api/v1/instance/settings/", {"externalChecksEnabled": False}, format="json",
        HTTP_HOST="127.0.0.1",
    )

    assert response.status_code == 200, response.content
    row.refresh_from_db()
    assert row.external_checks_enabled is False
    assert row.external_checks_revision == 1
    assert (row.public_host, row.public_port, row.public_scheme) == ("localhost", 5174, "http")


@pytest.mark.django_db
def test_service_announcements_are_readable_only_by_installation_admin():
    client = TenantAPIClient()
    path = "/api/v1/instance/update/announcements/"
    ordinary_user = HumanUser.objects.create_user(email="announcements-reader@example.test")
    client.force_authenticate(ordinary_user)
    assert client.get(path, HTTP_HOST="127.0.0.1").status_code == 403

    admin = HumanUser.objects.create_user(email="announcements-admin@example.test", is_instance_admin=True)
    client.force_authenticate(admin)
    assert finish_attempt(reserve_attempt(VERSION), CheckInResult(announcements=[]))
    response = client.get(path, HTTP_HOST="127.0.0.1")
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert response.json()["announcements"] == []
    assert set(response.json()) == {"enabled", "failed", "announcements", "expiresInMs"}


def test_parsing_preserves_order_text_and_only_allows_absolute_safe_links():
    links = ["https://example.com/path", "https://user@example.com/", "/help", "javascript:alert(1)", ""]
    entries = [
        {"id": idx, "title": "<b>Текст</b>", "text": "Раз.\n\nДва.", "link": link}
        for idx, link in enumerate(links, start=1)
    ]
    parsed = parse_announcements({"announcements": entries})
    assert parsed == [entries[0], *[dict(entry, link="") for entry in entries[1:]]]
    with pytest.raises(ValueError):
        parse_announcements({"announcements": [entries[0], {"id": 2}]})


@pytest.mark.django_db
def test_due_check_in_reads_current_address_and_respects_policy(monkeypatch, settings):
    requests = []

    async def prevent_network(_client, request):
        requests.append(request)
        raise httpx.ConnectError("Check-in request captured before network I/O", request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", prevent_network)
    monkeypatch.delenv("CHATBALLS_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("CHATBALLS_VERSION", "1.24.0-rc.1")
    settings.CHATBALLS_PUBLIC_BASE_URL = "http://localhost:8000"
    row = InstanceSettings.load()
    row.public_host, row.public_scheme, row.public_port = "chat.example.org", "https", 8443
    row.save()

    check_in_if_due()
    state = CheckInState.objects.get()
    assert state.installation_id.version == 4
    base = {"installation_id": str(state.installation_id), "version": "1.24.0-rc.1"}
    assert json.loads(requests[-1].content) == {**base, "public_url": "https://chat.example.org:8443"}
    assert requests[-1].method == "POST"
    assert str(requests[-1].url) == "https://bo.chatballs.ru/public/v1/installations/check-in/"

    def check_again():
        CheckInState.objects.update(next_attempt_at=timezone.now())
        check_in_if_due()

    row.public_host, row.public_scheme, row.public_port = "8.8.8.8", "http", 8080
    row.save()
    monkeypatch.setenv("CHATBALLS_VERSION", "1.24.0")
    check_in_if_due()
    base["version"] = "1.24.0"
    assert json.loads(requests[-1].content) == {**base, "public_url": "http://8.8.8.8:8080"}

    monkeypatch.setenv("CHATBALLS_PUBLIC_BASE_URL", "https://user:secret@public.example.org:443/chat?token=1#fragment")
    check_again()
    assert json.loads(requests[-1].content) == {**base, "public_url": "https://public.example.org:443/chat"}

    monkeypatch.delenv("CHATBALLS_PUBLIC_BASE_URL")
    row.public_host = ""
    row.save()
    check_again()
    assert json.loads(requests[-1].content) == base

    row.external_checks_enabled = False
    row.save()
    check_again()
    assert len(requests) == 4


@pytest.mark.parametrize("configured_url", [
    "ftp://chat.example.org", "https://chat.example.org:0", "https://chat.example.org:65536",
    "http://localhost:5173", "http://printer", "https://chat.internal.",
    "http://192.168.1.10:8080", "http://127.0.0.1", "http://100.64.0.1",
    "http://[::ffff:10.0.0.1]", "http://224.0.0.1", "http://[ff02::1]",
    "https://chat.example.org/" + "x" * 4096,
])
def test_request_omits_unsuitable_public_url(configured_url):
    installation_id = uuid4()
    request = _build_request(installation_id, "dev", configured_url)
    assert json.loads(request.content) == {"installation_id": str(installation_id), "version": "dev"}


def test_request_keeps_public_ipv6_address_and_port():
    request = _build_request(uuid4(), "dev", "https://[2606:4700:4700::1111]:8443")
    assert json.loads(request.content)["public_url"] == "https://[2606:4700:4700::1111]:8443"


@pytest.mark.parametrize("announcements", [[], [{"id": 1, "title": "Notice", "text": "Text", "link": ""}]])
def test_check_in_reads_success_response(announcements):
    response = httpx.Response(200, json={"announcements": announcements})
    assert _read_response(response) == CheckInResult(announcements=announcements)
