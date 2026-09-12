"""Проверка релизов и запрос установки обновления.

Приложение не перезапускает само себя: у публичного процесса нет и не должно
быть доступа к Docker. Оно лишь кладёт запрос в общий том
``CHATBALLS_UPDATES_DIR``, а сервис updater (deploy/updater) забирает его,
проверяет и выполняет ``docker compose pull && up`` уже снаружи. Состояние
установки updater пишет в тот же том файлом ``status``; приложение
переносит его в UpdateState при каждом чтении.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from chatballs.updates.github import (
    ReleaseChannelError,
    fetch_latest_release,
    is_newer,
)
from chatballs.updates.models import InstallStatus, UpdateState

logger = logging.getLogger(__name__)

REQUEST_FILE = "request.json"
STATUS_FILE = "status.json"
HEARTBEAT_FILE = "heartbeat"
# Пока updater не отметился дольше этого, считаем, что установки из интерфейса нет.
HEARTBEAT_STALE_SECONDS = 90
_STATUS_MAP = {
    "running": InstallStatus.RUNNING,
    "done": InstallStatus.DONE,
    "failed": InstallStatus.FAILED,
}


def updates_dir() -> Path:
    return Path(settings.CHATBALLS_UPDATES_DIR)


def check_for_updates(*, force: bool = False) -> UpdateState:
    """Спросить канал релизов, если пора (или если попросили явно)."""

    state = UpdateState.load()
    interval = timedelta(seconds=settings.CHATBALLS_UPDATE_CHECK_INTERVAL_SECONDS)
    if not force and state.checked_at and timezone.now() - state.checked_at < interval:
        return state
    try:
        release = fetch_latest_release()
    except ReleaseChannelError as error:
        state.check_error = str(error)[:500]
        state.checked_at = timezone.now()
        state.save(update_fields=["check_error", "checked_at"])
        logger.warning("Update check failed: %s", error)
        return state
    state.latest_version = release.version
    state.latest_name = release.name
    state.latest_notes = release.notes
    state.latest_published_at = release.published_at
    state.latest_compose_url = release.compose_url
    state.latest_page_url = release.page_url
    state.check_error = ""
    state.checked_at = timezone.now()
    state.save()
    return state


def update_available(state: UpdateState) -> bool:
    return bool(state.latest_version) and is_newer(state.latest_version, settings.CHATBALLS_VERSION)


def updater_online() -> bool:
    """Жив ли сервис updater: он отмечается в томе каждые несколько секунд."""

    path = updates_dir() / HEARTBEAT_FILE
    try:
        age = timezone.now().timestamp() - path.stat().st_mtime
    except OSError:
        return False
    return age < HEARTBEAT_STALE_SECONDS


def sync_install_status(state: UpdateState) -> UpdateState:
    """Перенести статус, который пишет updater, в состояние приложения."""

    if state.install_status not in {InstallStatus.REQUESTED, InstallStatus.RUNNING}:
        return state
    path = updates_dir() / STATUS_FILE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    if str(payload.get("version", "")) != state.install_version:
        return state
    status = _STATUS_MAP.get(str(payload.get("status", "")).lower())
    if status is None:
        return state
    message = str(payload.get("message", ""))[:1000]
    if status != state.install_status or message != state.install_message:
        state.install_status = status
        state.install_message = message
        state.install_updated_at = timezone.now()
        state.save(update_fields=["install_status", "install_message", "install_updated_at"])
    return state


class InstallNotPossible(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


def request_install(*, actor, state: UpdateState | None = None) -> UpdateState:
    """Положить запрос на установку последней версии в том updater'а."""

    from chatballs.i18n import t

    state = sync_install_status(state or UpdateState.load())
    if not update_available(state):
        raise InstallNotPossible(t("updates.nothing_to_install"), code="nothing_to_install")
    if not updater_online():
        raise InstallNotPossible(t("updates.updater_offline"), code="updater_offline")
    if state.install_status in {InstallStatus.REQUESTED, InstallStatus.RUNNING}:
        raise InstallNotPossible(t("updates.install_in_progress"), code="install_in_progress")
    directory = updates_dir()
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / REQUEST_FILE
    now = timezone.now()
    request_path.write_text(
        json.dumps(
            {
                "version": state.latest_version,
                "compose_url": state.latest_compose_url,
                "requested_at": now.isoformat(),
                "requested_by": getattr(actor, "email", ""),
            }
        ),
        encoding="utf-8",
    )
    # Прежний статус относится к прошлой установке: убрать, чтобы не спутать.
    try:
        (directory / STATUS_FILE).unlink()
    except OSError:
        pass
    state.install_version = state.latest_version
    state.install_status = InstallStatus.REQUESTED
    state.install_message = ""
    state.install_requested_at = now
    state.install_updated_at = now
    state.install_requested_by = actor if getattr(actor, "pk", None) else None
    state.save()
    return state


def update_payload(state: UpdateState) -> dict[str, object]:
    return {
        "currentVersion": settings.CHATBALLS_VERSION,
        "latestVersion": state.latest_version or None,
        "latestName": state.latest_name,
        "latestNotes": state.latest_notes,
        "latestPublishedAt": state.latest_published_at.isoformat() if state.latest_published_at else None,
        "latestPageUrl": state.latest_page_url,
        "available": update_available(state),
        "checkedAt": state.checked_at.isoformat() if state.checked_at else None,
        "checkError": state.check_error,
        "updaterOnline": updater_online(),
        "install": {
            "version": state.install_version or None,
            "status": state.install_status,
            "message": state.install_message,
            "requestedAt": state.install_requested_at.isoformat() if state.install_requested_at else None,
            "updatedAt": state.install_updated_at.isoformat() if state.install_updated_at else None,
        },
    }
