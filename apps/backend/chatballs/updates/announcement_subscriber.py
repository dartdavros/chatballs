"""A poller thread owns the outgoing publication stream under a PostgreSQL lock."""

import json
import logging
import os
import threading
from datetime import UTC, datetime

import httpx
from django.conf import settings
from django.db import close_old_connections, connections
from django.db.models.functions import Now

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.updates.announcement_state import save_schedule
from chatballs.updates.check_in_client import CHECK_IN_URL, _rate_limit_delay
from chatballs.updates.check_in_state import CheckInState

logger = logging.getLogger(__name__)
LEADER_LOCK = 738220951
_thread = None


def ensure_announcement_subscriber():
    global _thread
    if _thread is None or not _thread.is_alive():
        _thread = threading.Thread(target=_run, name="publication-subscriber", daemon=True)
        _thread.start()


def _configuration():
    instance = InstanceSettings.objects.get(pk=InstanceSettings.SINGLETON_PK)
    if not instance.external_checks_enabled:
        return None
    state, _ = CheckInState.objects.get_or_create(instance=instance)
    if CheckInState.objects.filter(pk=state.pk, announcement_retry_at__gt=Now()).exists():
        return None
    return instance.external_checks_revision, {
        "installation_id": str(state.installation_id),
        "version": os.environ.get("CHATBALLS_VERSION", settings.CHATBALLS_VERSION),
    }


def _still_enabled(revision):
    return InstanceSettings.objects.filter(pk=1, external_checks_enabled=True,
        external_checks_revision=revision).exists()


def _defer_retry(delay):
    state = CheckInState.objects.annotate(db_now=Now()).get(pk=1)
    deadline = state.db_now + min(delay, datetime.max.replace(tzinfo=UTC) - state.db_now)
    CheckInState.objects.filter(pk=state.pk).update(announcement_retry_at=deadline)


def _stream_url():
    base = CHECK_IN_URL.rsplit("check-in/", 1)[0]
    local_origin = os.environ.get("CHATBALLS_BACKOFFICE_BASE_URL", "")
    if settings.DEBUG and local_origin:
        base = local_origin.rstrip("/") + "/public/v1/installations/"
    return base + "publications/stream/"


def _receive(leader, revision, body):
    with httpx.Client(verify=True, follow_redirects=False, trust_env=False,
                     timeout=httpx.Timeout(20, connect=5)) as client:
        with client.stream("POST", _stream_url(), json=body, headers={"Accept": "text/event-stream"}) as response:
            if response.status_code == 429:
                _defer_retry(_rate_limit_delay(response.headers.get("Retry-After", "")))
                return 5
            response.raise_for_status()
            if not response.headers.get("Content-Type", "").startswith("text/event-stream"):
                raise ValueError("Invalid publication stream content type")
            data = []
            for line in response.iter_lines():
                # A failed leadership connection must never silently reconnect without its lock.
                with leader.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                if not _still_enabled(revision):
                    return 0
                if line.startswith("data:"):
                    data.append(line[5:].lstrip())
                elif not line and data:
                    if not save_schedule(json.loads("\n".join(data)), revision):
                        return 0
                    data.clear()
    return 2


def _run():
    delay = 0
    while True:
        threading.Event().wait(delay)
        delay = 5
        leader = connections["default"].copy(alias="publication-leader")
        # Session advisory locks must be released by closing the actual connection.
        # Returning it to Django's pool would keep the lock alive.
        leader.settings_dict["OPTIONS"] = {
            key: value for key, value in leader.settings_dict.get("OPTIONS", {}).items() if key != "pool"
        }
        try:
            with leader.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", [LEADER_LOCK])
                if not cursor.fetchone()[0]:
                    continue
            config = _configuration()
            if config is None:
                continue
            delay = _receive(leader, *config)
        except Exception:
            logger.warning("Publication stream interrupted", exc_info=False)
            delay = 15
        finally:
            leader.close()
            close_old_connections()
