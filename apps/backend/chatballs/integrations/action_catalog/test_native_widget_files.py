"""Widget images keep sanitization, tenant scope, real storage and file grants."""

import io

from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.models import WidgetAsset


class NativeWidgetFileTests(NativeFileCase):
    def execute(self, key, values, *, tenant=None):
        run, output = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        return run, output

    def test_upload_sanitized_download_and_delete_keep_storage_ownership(self):
        _, result = self.execute("connections.post", {"name": "Images", "provider": "WEB",
            "channelId": self.conversation.channel_id, "config": {"allowedOrigins": ["example.test"]}})
        identifier = result["integration"]["id"]
        content = b'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><script>bad()</script><circle r="40"/></svg>'
        reference = store_service_file(context=self.context, integration=None, name="icon.svg",
            content_type="image/svg+xml", stream=io.BytesIO(content), size=len(content))
        run, _ = self.execute("connections.assets.post", {"integration_id": identifier, "file": {"fileId": reference.file_id}})
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            row = WidgetAsset.objects.get(integration_id=identifier)
            public_id = str(row.public_id)
            storage, name = row.file.storage, row.file.name
        run, result = self.execute("connections.asset.get", {"public_id": public_id})
        received = self.read_result(run, result)[2]
        self.assertIn(b"circle", received)
        self.assertNotIn(b"script", received)
        self.assertNotIn(b"bad()", received)
        run, _ = execute_action(TenantContext.for_membership(self.foreign_member), "connections.asset.get", {"public_id": public_id})
        self.assertEqual(run.state, "failed")
        self.execute("connections.test.post", {"integration_id": identifier})
        self.execute("connections.detail.delete", {"integration_id": identifier})
        with tenant_atomic(self.context):
            self.assertFalse(WidgetAsset.objects.filter(integration_id=identifier).exists())
            self.assertFalse(storage.exists(name))
