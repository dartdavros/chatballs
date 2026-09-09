"""Границы, которые обходились через соседний эндпоинт.

Два места вели себя не так, как обещает соседняя ручка того же экрана:

- начало настройки 2FA молча выключало уже включённую, минуя и пароль, и
  требование организации, — то есть было бесплатным способом снять 2FA для
  того, у кого уже есть чужая сессия;
- сброс пароля по письму оставлял чужие сессии живыми, хотя пароль сбрасывают
  как раз тогда, когда доступ мог оказаться у чужого.
"""

from __future__ import annotations

from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from chatballs.identity.auth.totp_utils import _generate_totp_secret
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.testing import TenantAPIClient

PASSWORD = "Owner-Password-2026!"
NEW_PASSWORD = "Owner-Password-2027!"


class TotpSetupStartTests(TestCase):
    def setUp(self) -> None:
        self.result = bootstrap_owner(email="totp-owner@example.com", password=PASSWORD)
        self.owner = self.result.owner
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)

    def test_start_issues_a_secret_while_totp_is_off(self) -> None:
        self.owner.totp_secret = "OLDSECRET"
        self.owner.save(update_fields=["totp_secret"])

        response = self.client.post("/api/v1/auth/profile/totp/start/")

        self.assertEqual(response.status_code, 200, response.content)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.totp_secret, "")
        self.assertFalse(self.owner.totp_enabled)

    def test_start_cannot_disable_enabled_totp(self) -> None:
        secret = _generate_totp_secret()
        self.owner.totp_secret = secret
        self.owner.totp_enabled = True
        self.owner.save(update_fields=["totp_secret", "totp_enabled"])

        response = self.client.post("/api/v1/auth/profile/totp/start/")

        self.assertEqual(response.status_code, 409, response.content)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.totp_enabled)
        self.assertEqual(self.owner.totp_secret, secret)

    def test_disable_still_requires_the_current_password(self) -> None:
        self.owner.totp_secret = _generate_totp_secret()
        self.owner.totp_enabled = True
        self.owner.save(update_fields=["totp_secret", "totp_enabled"])

        rejected = self.client.post(
            "/api/v1/auth/profile/totp/disable/",
            {"currentPassword": "wrong-password"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.content)

        accepted = self.client.post(
            "/api/v1/auth/profile/totp/disable/",
            {"currentPassword": PASSWORD},
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.totp_enabled)


class PasswordResetSessionTests(TestCase):
    def setUp(self) -> None:
        self.result = bootstrap_owner(email="reset-owner@example.com", password=PASSWORD)
        self.owner = self.result.owner

    def _reset_link(self) -> tuple[str, str]:
        # Токен считается от текущего состояния пользователя (в том числе
        # last_login), поэтому берём его после всех входов.
        self.owner.refresh_from_db()
        return (
            urlsafe_base64_encode(force_bytes(self.owner.pk)),
            default_token_generator.make_token(self.owner),
        )

    def _session_keys(self) -> set[str]:
        keys = set()
        for session in Session.objects.all():
            if str(session.get_decoded().get("_auth_user_id", "")) == str(self.owner.pk):
                keys.add(session.session_key)
        return keys

    def test_reset_revokes_existing_sessions(self) -> None:
        stolen = TenantAPIClient()
        self.assertTrue(stolen.login(email=self.owner.email, password=PASSWORD))
        self.assertTrue(self._session_keys())

        uid, token = self._reset_link()
        anonymous = TenantAPIClient()
        response = anonymous.post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "newPassword": NEW_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertGreaterEqual(response.json()["revoked"], 1)
        self.assertEqual(self._session_keys(), set())

        # Прежняя сессия больше не открывает приложение.
        session = stolen.get("/api/v1/auth/session/")
        self.assertFalse(session.json()["authenticated"])

    def test_reset_still_sets_the_new_password(self) -> None:
        uid, token = self._reset_link()
        TenantAPIClient().post(
            "/api/v1/auth/password-reset/confirm/",
            {"uid": uid, "token": token, "newPassword": NEW_PASSWORD},
            format="json",
        )

        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password(NEW_PASSWORD))
        self.assertFalse(self.owner.must_change_password)
