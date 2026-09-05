import base64
import hashlib
import hmac
import time

from django.test import SimpleTestCase, override_settings

from chatballs.calls.serializers import ice_servers_payload
from chatballs.calls.turn import turn_credentials

SECRET = "coturn-shared-secret"
TURN_URLS = ["turn:hub.edevs.tech:3478?transport=udp", "turn:hub.edevs.tech:3478?transport=tcp"]
STUN_URLS = ["stun:hub.edevs.tech:3478"]


def _expected_credential(username: str, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


@override_settings(CHATBALLS_CALL_TURN_SECRET=SECRET, CHATBALLS_CALL_TURN_TTL_SECONDS=3600)
class TurnCredentialsTests(SimpleTestCase):
    def test_username_encodes_expiry_and_label(self) -> None:
        before = int(time.time())
        username, _credential = turn_credentials(label="hub")
        expiry_str, _, label = username.partition(":")
        self.assertEqual(label, "hub")
        expiry = int(expiry_str)
        self.assertGreaterEqual(expiry, before + 3600)
        self.assertLessEqual(expiry, int(time.time()) + 3600 + 5)

    def test_credential_is_hmac_sha1_of_username(self) -> None:
        username, credential = turn_credentials(now=1_700_000_000)
        self.assertEqual(username, "1700003600:hub")
        self.assertEqual(credential, _expected_credential(username))

    def test_credential_rotates_with_secret(self) -> None:
        _u, credential = turn_credentials(now=1_700_000_000)
        with override_settings(CHATBALLS_CALL_TURN_SECRET="other-secret"):
            _u2, other = turn_credentials(now=1_700_000_000)
        self.assertNotEqual(credential, other)


class IceServersPayloadTests(SimpleTestCase):
    @override_settings(CHATBALLS_CALL_STUN_URLS=[], CHATBALLS_CALL_TURN_URLS=[], CHATBALLS_CALL_TURN_SECRET="")
    def test_empty_without_configuration(self) -> None:
        self.assertEqual(ice_servers_payload(), [])

    @override_settings(CHATBALLS_CALL_STUN_URLS=STUN_URLS, CHATBALLS_CALL_TURN_URLS=[], CHATBALLS_CALL_TURN_SECRET="")
    def test_stun_only(self) -> None:
        servers = ice_servers_payload()
        self.assertEqual(servers, [{"urls": STUN_URLS}])

    @override_settings(
        CHATBALLS_CALL_STUN_URLS=STUN_URLS,
        CHATBALLS_CALL_TURN_URLS=TURN_URLS,
        CHATBALLS_CALL_TURN_SECRET=SECRET,
        CHATBALLS_CALL_TURN_TTL_SECONDS=3600,
    )
    def test_direct_first_then_turn_fallback(self) -> None:
        servers = ice_servers_payload()
        self.assertEqual(len(servers), 2)
        # STUN (direct-first) идёт перед TURN (fallback).
        self.assertEqual(servers[0], {"urls": STUN_URLS})
        turn = servers[1]
        self.assertEqual(turn["urls"], TURN_URLS)
        self.assertIn(":hub", turn["username"])
        self.assertEqual(turn["credential"], _expected_credential(turn["username"]))

    @override_settings(CHATBALLS_CALL_STUN_URLS=[], CHATBALLS_CALL_TURN_URLS=TURN_URLS, CHATBALLS_CALL_TURN_SECRET="")
    def test_turn_urls_without_secret_are_not_exposed(self) -> None:
        # Без секрета выдать рабочие credentials нельзя — TURN не отдаётся вовсе.
        self.assertEqual(ice_servers_payload(), [])
