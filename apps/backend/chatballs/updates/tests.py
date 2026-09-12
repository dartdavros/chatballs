"""Обновления из интерфейса: канал релизов, запрос установки, статус, права."""

from __future__ import annotations

import io
import json
import os
import time
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.testing import TenantAPIClient
from chatballs.updates import github, services
from chatballs.updates.models import InstallStatus, UpdateState

PASSWORD = "Owner-Password-2026!"

RELEASE = {
    "tag_name": "v1.5.0",
    "name": "v1.5.0",
    "body": "## Что нового\n- тест",
    "published_at": "2026-09-13T10:00:00Z",
    "html_url": "https://github.com/dartdavros/chatballs/releases/tag/v1.5.0",
    "assets": [
        {"name": "compose.yaml", "browser_download_url": "https://github.com/dartdavros/chatballs/releases/download/v1.5.0/compose.yaml"},
        {"name": "release.env", "browser_download_url": "https://github.com/dartdavros/chatballs/releases/download/v1.5.0/release.env"},
    ],
}


def _response(payload: dict) -> mock.MagicMock:
    """urlopen отдаёт контекстный менеджер с read(): подделываем ровно это."""

    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
    return response


class VersionTests(TestCase):
    def test_semantic_comparison(self) -> None:
        self.assertTrue(github.is_newer("1.5.0", "1.4.0"))
        self.assertTrue(github.is_newer("1.10.0", "1.9.9"))
        self.assertTrue(github.is_newer("1.5.0", "1.5.0-rc1"))
        self.assertFalse(github.is_newer("1.4.0", "1.4.0"))
        self.assertFalse(github.is_newer("1.3.9", "1.4.0"))
        # Dev-сборка: сравнивать не с чем.
        self.assertFalse(github.is_newer("1.5.0", "dev"))

    def test_tag_parsing(self) -> None:
        self.assertEqual(github.parse_version("v1.5.0"), "1.5.0")
        self.assertEqual(github.parse_version("1.5.0-rc1"), "1.5.0-rc1")
        self.assertIsNone(github.parse_version("release-1"))
        self.assertIsNone(github.parse_version("v1.5"))


@override_settings(CHATBALLS_VERSION="1.4.0", CHATBALLS_UPDATE_REPO="dartdavros/chatballs")
class UpdateCheckTests(TestCase):
    def test_check_records_latest_release(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_response(RELEASE)):
            state = services.check_for_updates(force=True)

        self.assertEqual(state.latest_version, "1.5.0")
        self.assertEqual(state.latest_compose_url, RELEASE["assets"][0]["browser_download_url"])
        self.assertEqual(state.check_error, "")
        self.assertTrue(services.update_available(state))

    def test_check_respects_interval_unless_forced(self) -> None:
        state = UpdateState.load()
        state.checked_at = timezone.now() - timedelta(minutes=5)
        state.save()
        with mock.patch("urllib.request.urlopen") as fetch:
            services.check_for_updates()
        fetch.assert_not_called()

    def test_channel_error_is_recorded_not_raised(self) -> None:
        with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
            state = services.check_for_updates(force=True)
        self.assertIn("offline", state.check_error)
        self.assertFalse(services.update_available(state))

    def test_release_without_compose_asset_is_refused(self) -> None:
        release = {**RELEASE, "assets": []}
        with mock.patch("urllib.request.urlopen", return_value=_response(release)):
            state = services.check_for_updates(force=True)
        self.assertIn("compose.yaml", state.check_error)
        self.assertEqual(state.latest_version, "")


@override_settings(CHATBALLS_VERSION="1.4.0", CHATBALLS_UPDATE_REPO="dartdavros/chatballs")
class InstallRequestTests(TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(CHATBALLS_UPDATES_DIR=self.tmp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.result = bootstrap_owner(email="update-owner@example.com", password=PASSWORD)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.result.owner)
        with mock.patch("urllib.request.urlopen", return_value=_response(RELEASE)):
            services.check_for_updates(force=True)

    def _heartbeat(self) -> None:
        (services.updates_dir() / services.HEARTBEAT_FILE).write_text("", encoding="utf-8")

    def test_install_needs_a_live_updater(self) -> None:
        response = self.client.post("/api/v1/instance/update/install/", {}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "updater_offline")

    def test_install_writes_request_and_tracks_status_from_updater(self) -> None:
        self._heartbeat()

        response = self.client.post("/api/v1/instance/update/install/", {}, format="json")

        self.assertEqual(response.status_code, 202, response.content)
        request = json.loads((services.updates_dir() / services.REQUEST_FILE).read_text(encoding="utf-8"))
        self.assertEqual(request["version"], "1.5.0")
        self.assertEqual(request["compose_url"], RELEASE["assets"][0]["browser_download_url"])
        self.assertEqual(response.json()["update"]["install"]["status"], InstallStatus.REQUESTED)

        # Повторный запрос, пока идёт установка, отклоняется.
        again = self.client.post("/api/v1/instance/update/install/", {}, format="json")
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["code"], "install_in_progress")

        # Updater пишет статус в том — приложение подхватывает его при чтении.
        (services.updates_dir() / services.STATUS_FILE).write_text(
            json.dumps({"status": "running", "version": "1.5.0", "message": "pulling"}), encoding="utf-8"
        )
        state = self.client.get("/api/v1/instance/update/").json()["update"]
        self.assertEqual(state["install"]["status"], InstallStatus.RUNNING)
        self.assertEqual(state["install"]["message"], "pulling")

        (services.updates_dir() / services.STATUS_FILE).write_text(
            json.dumps({"status": "done", "version": "1.5.0", "message": "updated"}), encoding="utf-8"
        )
        state = self.client.get("/api/v1/instance/update/").json()["update"]
        self.assertEqual(state["install"]["status"], InstallStatus.DONE)

    def test_status_for_another_version_is_ignored(self) -> None:
        self._heartbeat()
        self.client.post("/api/v1/instance/update/install/", {}, format="json")
        (services.updates_dir() / services.STATUS_FILE).write_text(
            json.dumps({"status": "done", "version": "1.4.9", "message": "stale"}), encoding="utf-8"
        )
        state = self.client.get("/api/v1/instance/update/").json()["update"]
        self.assertEqual(state["install"]["status"], InstallStatus.REQUESTED)

    def test_stale_heartbeat_means_offline(self) -> None:
        path = services.updates_dir() / services.HEARTBEAT_FILE
        path.write_text("", encoding="utf-8")
        old = time.time() - services.HEARTBEAT_STALE_SECONDS - 5
        os.utime(path, (old, old))
        self.assertFalse(services.updater_online())

    def test_organization_owner_reads_but_cannot_install_or_check(self) -> None:
        other = Organization.objects.create(name="Other", slug="other-upd")
        owner = HumanUser.objects.create_user(email="other-owner@example.com", password=PASSWORD)
        OrganizationMembership.objects.create(organization=other, user=owner, role=EmployeeRole.OWNER, position_title="Owner")
        client = TenantAPIClient()
        client.force_authenticate(owner)

        self.assertEqual(client.get("/api/v1/instance/update/").status_code, 200)
        self.assertEqual(client.post("/api/v1/instance/update/check/", {}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/v1/instance/update/install/", {}, format="json").status_code, 403)
