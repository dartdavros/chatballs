"""Portal files travel through real storage and execution-owned references."""

import io

from chatballs.integrations.action_catalog.native_file_test_base import NativeFileCase
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.files import store_service_file
from chatballs.support_portals.models import PortalArticleFile
from chatballs.tenancy.database import tenant_atomic


class NativePortalFileTests(NativeFileCase):
    def execute(self, key, values):
        run, output = execute_action(self.context, key, values)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        return run, output

    def test_upload_read_and_delete_preserve_bytes_and_quota_backed_file_ownership(self):
        _, result = self.execute("portals.post", {"name": "Files", "slug": "native-files"})
        values = {"portal_id": result["portal"]["id"]}
        _, result = self.execute("portals.categories.post", {**values, "name": "Files"})
        _, result = self.execute("portals.articles.post", {**values, "categoryId": result["category"]["id"],
            "slug": "files", "title": "Files", "content": "Attachments"})
        values["article_id"] = result["article"]["id"]
        content = b"Native portal file content."
        reference = store_service_file(context=self.context, integration=None, name="guide.txt",
            content_type="text/plain", stream=io.BytesIO(content), size=len(content))
        _, result = self.execute("portals.article.files.post", {**values, "file": {"fileId": reference.file_id}})
        identifier = result["file"]["id"]
        with tenant_atomic(self.context):
            row = PortalArticleFile.objects.get(pk=identifier)
            public_id = str(row.public_id)
            storage, name = row.file.storage, row.file.name
        run, result = self.execute("portals.file.get", {"public_id": public_id})
        self.assertEqual(self.read_result(run, result)[2], content)
        _, result = self.execute("portals.article.files.get", values)
        self.assertEqual(result["items"][0]["size"], len(content))
        self.execute("portals.article.file.delete", {**values, "file_id": identifier})
        with tenant_atomic(self.context):
            self.assertFalse(PortalArticleFile.objects.filter(pk=identifier).exists())
            self.assertFalse(storage.exists(name))
