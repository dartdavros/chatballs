"""Global permissions and shared services, using only the isolated test database."""

import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.identity.models import HumanUser
from chatballs.integrations.action_catalog.authority import AuthorityContext
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied, NativeContext
from chatballs.integrations.action_catalog.registry import (
    action_schemas,
    native_action,
    native_actions,
)
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.actions import native_operation
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.tenancy import storage_commands
from chatballs.tenancy import storage_settings as ss
from chatballs.testing import TenantAPIClient


class InstallationActionTests(TestCase):
    def setUp(self):
        self.user = HumanUser.objects.create_user(email="native-installation@example.test", is_instance_admin=True)
        self.context = AuthorityContext("instance", user=self.user)

    def invoke(self, key, values=None, context=None):
        action = native_action(key, authority="instance")
        result = action.execute(context or self.context, values or {})
        self.assertEqual(validate_value(action.operation.output, result.data), [])
        return result.data

    def test_global_actions_cannot_enter_any_tenant_catalog_or_resolution(self):
        globals = [action for action in native_actions(authority=None) if action.authority != "tenant"]
        self.assertTrue(globals)
        tenant_keys = {a.key for a in action_schemas()}
        for action in globals:
            self.assertNotIn(action.key, tenant_keys)
            self.assertIsNone(native_action(action.key))
            with self.assertRaises(ExecutionDenied):
                native_operation(action.key)
            with self.assertRaises(NativeAccessDenied):
                action.execute(NativeContext(None, "effect", "run", "step"), {})

    def test_settings_preserve_password_and_match_http_projection(self):
        self.invoke("instance.settings.patch", {"publicHost": "127.0.0.1", "email": {"password": "DoNotExpose-176"}})
        data = self.invoke("instance.settings.patch", {"email": {"password": ""}})
        self.assertTrue(data["instance"]["email"]["hasPassword"])
        self.assertEqual(InstanceSettings.load().email_password, "DoNotExpose-176")
        self.assertNotIn("DoNotExpose-176", json.dumps(data))
        client = TenantAPIClient()
        client.force_authenticate(self.user)
        self.assertEqual(client.get("/api/v1/instance/settings/", HTTP_HOST="127.0.0.1").json(), self.invoke("instance.settings.get"))

    def test_revoked_global_flag_is_checked_again_for_saved_context(self):
        HumanUser.objects.filter(pk=self.user.pk).update(is_instance_admin=False)
        with self.assertRaises(NativeAccessDenied):
            self.invoke("instance.network.patch", {"enabled": True})
        self.assertFalse(InstanceSettings.load().tools_private_network)

    def test_storage_result_does_not_disclose_provider_errors_or_masked_keys(self):
        row = ss.StorageSettings.load()
        row.s3_access_key = "SecretAccessKey176"
        row.s3_last_error = "SecretAccessKey176"
        row.migration_error = "SecretAccessKey176"
        row.save()
        data = self.invoke("instance.storage.get")
        self.assertNotIn("SecretAccessKey176", json.dumps(data))
        self.assertEqual(data["storage"]["s3AccessKeyMasked"], "")

    def test_probe_cannot_overwrite_newer_settings_or_revoked_authority(self):
        row = ss.StorageSettings.load()
        values = {"backend": "S3", "s3Bucket": "bucket", "s3AccessKey": "key", "s3SecretKey": "secret"}

        def concurrent_change(_config):
            newer = ss.StorageSettings.load()
            newer.s3_bucket = "newer"
            newer.migration_done = 7
            newer.save()

        with patch.object(ss, "probe_s3", side_effect=concurrent_change):
            result = storage_commands.update(self.user, values)
        self.assertEqual(result.status, 409)
        row.refresh_from_db()
        self.assertEqual((row.s3_bucket, row.migration_done), ("newer", 7))
        with patch.object(ss, "probe_s3", side_effect=lambda _config: HumanUser.objects.filter(pk=self.user.pk).update(is_instance_admin=False)):
            with self.assertRaises(PermissionDenied):
                storage_commands.update(self.user, values)
        row.refresh_from_db()
        self.assertEqual(row.backend, "LOCAL")
