"""Real multipart/storage boundary; no network service or shared account mutation."""

import hashlib
import struct
import zlib
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.test import AsyncClient
from django.utils import timezone

from chatballs.ai.external_agents.file_access import grant_message
from chatballs.ai.external_agents.file_cleanup import cleanup
from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.conversations.models import Message
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.models import OrganizationStorageUsage


class FileTests(MediaCase):
    def test_asgi_download_remains_a_bounded_async_stream(self):
        row = self.request()
        data = b"x" * 150000
        receipt = self.upload(row, data).json()

        async def download():
            client = AsyncClient()
            response = await client.get(self.root + f"files/{receipt['fileId']}/",
                {"authorizationId": str(row.authorization_id)},
                headers={"Authorization": "Bearer " + self.created["incomingKey"]})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.is_async)
            chunks = [part async for part in response.streaming_content]
            self.assertEqual([len(part) for part in chunks], [65536, 65536, 18928])
            self.assertEqual(b"".join(chunks), data)

        async_to_sync(download)()

    def test_real_image_trigger_and_upload_use_scoped_bytes(self):
        def chunk(kind, body):
            return struct.pack("!I", len(body)) + kind + body + struct.pack("!I", zlib.crc32(kind + body))

        header = struct.pack("!IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
        pixels = (b"\x00" + b"\x00\x00\xff" * 2) * 2
        data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))
        row = self.request("picture", kind="file", attachment=ContentFile(data, name="photo.png"),
            attachment_name="photo.png", attachment_content_type="image/png", attachment_size=len(data))
        self.assertIsNotNone(self.claim())
        row.refresh_from_db()
        trigger = open_payload(row.snapshot_ciphertext)["trigger"]
        self.assertEqual(trigger["type"], "image")
        self.assertEqual(trigger["attachments"][0]["mimeType"], "image/png")
        response = self.download(row, trigger["attachments"][0]["fileId"])
        self.assertEqual(b"".join(response.streaming_content), data)
        upload = self.upload(row, data, "out.png", "image/png")
        self.assertEqual(upload.status_code, 201, upload.content)
        body = self.result(row)
        content = self.file_content(upload.json())
        content["type"] = "image"
        body["outcome"]["messages"][0]["content"] = content
        self.assertEqual(self.callback(row, body).status_code, 202)

    def test_stream_upload_repeat_digest_metadata_conflict_and_private_download(self):
        row = self.request()
        upload_id = uuid4()
        response = self.upload(row, upload_id=upload_id, name='unsafe\r\n"document.txt')
        self.assertEqual(response.status_code, 201, response.content)
        receipt = response.json()
        self.assertNotIn("\r", receipt["filename"])
        repeat = self.upload(row, upload_id=upload_id, name='unsafe\r\n"document.txt')
        self.assertEqual((repeat.status_code, repeat.json()), (200, receipt))
        self.assertEqual(self.upload(row, b"changed", upload_id=upload_id).status_code, 409)
        self.assertEqual(self.upload(row, sha256="0" * 64).status_code, 400)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
        result = self.download(row, receipt["fileId"])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result["Cache-Control"], "no-store")
        self.assertEqual(result["X-Content-Type-Options"], "nosniff")
        self.assertTrue(result["Content-Disposition"].startswith("attachment;"))
        self.assertEqual(b"".join(result.streaming_content), b"private document")
        ranged = self.client.get(self.root + f"files/{receipt['fileId']}/",
            {"authorizationId": str(row.authorization_id)}, HTTP_RANGE="bytes=0-1", **self.header)
        self.assertEqual(ranged.status_code, 200)
        self.assertEqual(b"".join(ranged.streaming_content), b"private document")
        self.assertEqual(OrganizationStorageUsage.objects.get(organization=self.organization).bytes_used, receipt["size"])

    def test_audio_active_types_urls_empty_and_size_rejected(self):
        row = self.request()
        for data, name, mime in [(b"OggSvoice", "voice.bin", "application/octet-stream"),
                                 (b"audio", "voice.mp3", "text/plain"),
                                 (b"<svg/>", "image.svg", "image/svg+xml"),
                                 (b"MZbinary", "a.bin", "application/octet-stream"),
                                 (b"", "empty.txt", "text/plain")]:
            with self.subTest(name):
                self.assertEqual(self.upload(row, data, name, mime).status_code, 422)
        self.assertEqual(self.upload(row, url="https://private.invalid").status_code, 400)
        self.assertEqual(self.upload(row, b"x" * (20 * 1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(ExternalAgentFile.objects.count(), 0)

    def test_storage_interruption_retry_and_orphan_cleanup(self):
        row = self.request()
        identifier = uuid4()

        def interrupted(record, upload):
            default_storage.save(record.file.name, ContentFile(b"partial bytes"))
            raise OSError("interrupted")

        with patch("chatballs.ai.external_agents.file_views.write", side_effect=interrupted):
            response = self.upload(row, upload_id=identifier)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"interrupted", response.content)
        record = ExternalAgentFile.objects.get()
        self.assertFalse(record.complete)
        self.assertTrue(record.released)
        with tenant_atomic(self.context):
            self.assertFalse(default_storage.exists(record.file.name))
        self.assertEqual(self.download(row, record.public_id).status_code, 404)
        response = self.upload(row, upload_id=identifier)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["fileId"], str(record.public_id))
        with patch("chatballs.ai.external_agents.file_cleanup.timezone.now", return_value=timezone.now() + timedelta(days=2)):
            with tenant_atomic(self.context):
                self.assertEqual(cleanup(self.context), 1)
        record.refresh_from_db()
        self.assertTrue(record.released)
        self.assertEqual(OrganizationStorageUsage.objects.get(organization=self.organization).bytes_used, 0)

    def test_truncated_multipart_is_unpublished_and_full_retry_is_safe(self):
        row = self.request()
        identifier = uuid4()
        data = b"complete document"
        fields = {"uploadId": str(identifier), "authorizationId": str(row.authorization_id),
                  "sha256": hashlib.sha256(data).hexdigest()}
        raw = b"".join(f'--t190-stream\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
                       for key, value in fields.items())
        raw += (b'--t190-stream\r\nContent-Disposition: form-data; name="file"; filename="doc.txt"\r\n'
                b'Content-Type: text/plain\r\n\r\npartial')
        response = self.client.generic("POST", self.root + "files/", raw,
            content_type="multipart/form-data; boundary=t190-stream", HTTP_IDEMPOTENCY_KEY=str(identifier), **self.header)
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(ExternalAgentFile.objects.filter(complete=True).exists())
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
        self.assertEqual(self.upload(row, data, upload_id=identifier).status_code, 201)

    def test_trigger_history_grants_exclude_future_and_unissued_files(self):
        def attachment(text):
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT", kind="file",
                text=text, attachment_name="incoming.txt", attachment_content_type="text/plain", attachment_size=8)
            with tenant_atomic(self.context):
                message.attachment.save("incoming.txt", ContentFile(b"incoming"))
            return message

        old = attachment("old")
        for index in range(21):
            Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=str(index))
        row = self.request()
        future = attachment("future")
        self.assertIsNotNone(self.claim())
        record = ExternalAgentFile.objects.get(source_message=old)
        self.assertEqual(self.download(row, record.public_id).status_code, 404)
        row.refresh_from_db()
        snapshot = open_payload(row.snapshot_ciphertext)
        query = {"authorizationId": str(row.authorization_id),
                 "snapshotCursor": snapshot["context"]["history"]["snapshotCursor"], "pageSize": 200}
        result = self.client.get(self.root + "history/", query, **self.header)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertFalse(ExternalAgentFile.objects.filter(source_message=future).exists())
        with tenant_atomic(self.context):
            unissued_future = grant_message(row, future)
        self.assertEqual(self.download(row, unissued_future["fileId"]).status_code, 404)
        self.assertEqual(self.download(row, record.public_id).status_code, 200)
        old.delete()
        self.assertEqual(self.download(row, record.public_id).status_code, 404)

    def test_feature_revoke_closes_upload_and_download_and_files_have_rls(self):
        row = self.request()
        receipt = self.upload(row).json()
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertEqual(ExternalAgentFile.objects.count(), 0)
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.assertEqual(self.download(row, receipt["fileId"]).status_code, 403)
        self.assertEqual(self.upload(row).status_code, 403)

    def test_policy_change_closes_previously_uploaded_file(self):
        row = self.request()
        receipt = self.upload(row).json()
        self.bind(self.connection.pk, standardFields=["name"])
        self.assertEqual(self.download(row, receipt["fileId"]).status_code, 403)
