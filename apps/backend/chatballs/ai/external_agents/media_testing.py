"""Helpers only for the isolated test database and controlled native transport calls."""

import hashlib
from tempfile import TemporaryDirectory
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from chatballs.ai.external_agents.runtime_testing import RuntimeData


class MediaCase(RuntimeData, TestCase):
    def setUp(self):
        super().setUp()
        media = self.enterContext(TemporaryDirectory(prefix="chatballs-t190-"))
        self.enterContext(override_settings(MEDIA_ROOT=media))
        self.root = (f"/api/v1/external-agent/connections/{self.connection.pk}"
                     f"/conversations/{self.conversation.pk}/")
        self.header = {"HTTP_AUTHORIZATION": "Bearer " + self.created["incomingKey"]}

    def upload(self, row, data=b"private document", name="document.txt", mime="text/plain", upload_id=None, **values):
        identifier = str(upload_id or uuid4())
        body = {"uploadId": identifier, "authorizationId": str(row.authorization_id),
                "file": SimpleUploadedFile(name, data, content_type=mime),
                "sha256": hashlib.sha256(data).hexdigest(), **values}
        return self.client.post(self.root + "files/", body, format="multipart",
                               HTTP_IDEMPOTENCY_KEY=identifier, **self.header)

    def download(self, row, identifier):
        return self.client.get(self.root + f"files/{identifier}/", {"authorizationId": str(row.authorization_id)}, **self.header)

    def file_content(self, receipt, caption="document"):
        return {"type": "file", "fileId": receipt["fileId"], "filename": receipt["filename"],
                "mimeType": receipt["mimeType"], "size": receipt["size"], "sha256": receipt["sha256"], "caption": caption}
