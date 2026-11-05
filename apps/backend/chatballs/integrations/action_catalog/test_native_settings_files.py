"""Logo operations use real tenant storage and native execution file ownership."""

from io import BytesIO

from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.tenancy.database import tenant_atomic


class NativeSettingsFileTests(NativeFileCase):
    def test_upload_read_and_delete_logo(self):
        content = b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16"/></svg>'
        file = store_service_file(context=self.context, integration=None, name="logo.svg", content_type="image/svg+xml",
            stream=BytesIO(content), size=len(content))
        run, _ = execute_action(self.context, "settings.logo.post", {"file": {"fileId": file.file_id}})
        self.assertEqual(run.state, "completed")
        run, output = execute_action(self.context, "settings.logo.get", {})
        _name, content_type, data = self.read_result(run, output)
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(data, content)
        run, _ = execute_action(self.context, "settings.logo.delete", {})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.organization.refresh_from_db()
            self.assertFalse(self.organization.logo)
