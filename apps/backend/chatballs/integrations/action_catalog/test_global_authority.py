"""Global caller isolation, using the existing services and isolated test DB."""

from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone

from chatballs.identity.models import HumanUser, Organization
from chatballs.integrations.action_catalog.authority import AuthorityContext
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.adapters.schema import validate_value
from chatballs.platform.models import PlatformToken
from chatballs.platform.testing import create_platform_operator


class GlobalAuthorityTests(TestCase):
    def invoke(self, key, context, values=None):
        action = native_action(key, authority=context.authority)
        result = action.execute(context, values or {})
        self.assertEqual(validate_value(action.operation.output, result.data), [])
        return result.data

    def test_personal_changes_and_session_revocation_stay_with_the_live_caller(self):
        user = HumanUser.objects.create_user(email="personal176@example.test")
        other = HumanUser.objects.create_user(email="other176@example.test")
        clients = [Client(), Client(), Client()]
        for client, owner in zip(clients, (user, user, other), strict=True):
            client.force_login(owner)
        keys = [client.session.session_key for client in clients]
        context = AuthorityContext("personal", user=user, session_key=keys[0])
        data = self.invoke("profile.patch", context, {"fullName": "Native user", "email": user.email})
        self.assertEqual(data["user"]["id"], user.pk)
        other.refresh_from_db()
        self.assertNotEqual(other.full_name, "Native user")
        self.invoke("profile.sessions.get", context)
        self.assertEqual(self.invoke("profile.sessions.revoke", context), {"revoked": 1})
        self.assertTrue(Session.objects.filter(session_key=keys[0]).exists())
        self.assertFalse(Session.objects.filter(session_key=keys[1]).exists())
        self.assertTrue(Session.objects.filter(session_key=keys[2]).exists())
        for invalid_key in (keys[1], keys[2], ""):
            with self.assertRaises(NativeAccessDenied):
                self.invoke("profile.sessions.revoke", AuthorityContext("personal", user=user, session_key=invalid_key))
        HumanUser.objects.filter(pk=user.pk).update(is_active=False)
        with self.assertRaises(NativeAccessDenied):
            self.invoke("profile.appearance.patch", context, {"theme": "DARK"})

    def test_platform_replay_and_revocation_use_the_existing_token(self):
        operator, _ = create_platform_operator()
        token = PlatformToken.objects.get(operator=operator)
        HumanUser.objects.create_user(email="platform-owner176@example.test")
        context = AuthorityContext("platform", user=operator, token=token)
        values = {"name": "Native platform", "slug": "native-platform-176", "timezone": "UTC",
            "owner_email": "platform-owner176@example.test", "idempotencyKey": "native-platform176"}
        first = self.invoke("platform.organizations.provision", context, values)
        self.assertEqual(self.invoke("platform.organizations.provision", context, values), first)
        self.assertEqual(Organization.objects.filter(slug=values["slug"]).count(), 1)
        PlatformToken.objects.filter(pk=token.pk).update(revoked_at=timezone.now())
        with self.assertRaises(NativeAccessDenied):
            self.invoke("platform.organizations.provision", context, values)

    def test_closed_bootstrap_cannot_create_another_owner(self):
        Organization.objects.create(name="Existing", slug="existing176")
        context = AuthorityContext("bootstrap", public_host="127.0.0.1", public_scheme="http")
        self.assertEqual(self.invoke("setup.get", context), {"needsSetup": False})
        with self.assertRaises(NativeAccessDenied):
            self.invoke("setup.complete", context, {"organizationName": "Forbidden", "fullName": "Owner",
                "email": "bootstrap176@example.test", "password": "NeverPersist176!"})
        self.assertFalse(HumanUser.objects.filter(email="bootstrap176@example.test").exists())
