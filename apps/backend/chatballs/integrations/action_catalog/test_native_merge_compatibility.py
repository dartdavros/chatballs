"""Preserve speech configuration and receipt semantics across the main merge."""

import json
from unittest.mock import patch

from django.db import connection

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution import native_results
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient


class NativeMergeCompatibilityTests(CommentTransactionTestBase):
    def execute(self, key, values):
        run, result = execute_action(self.context, key, values)
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        return run, result

    def client_for_owner(self):
        client = TenantAPIClient()
        client.force_authenticate(self.author)
        return client

    def test_speech_check_uses_shared_io_boundary_and_preserves_revision_and_secrets(self):
        secret = "SpeechMergeCredential42"
        _, result = self.execute("connections.post", {"name": "Speech", "provider": "YANDEX_SPEECHKIT",
            "secret": secret, "config": {"folderId": "unit-folder", "transcriptionModel": "general"}})
        identifier = result["integration"]["id"]
        self.assertEqual(result["integration"]["kind"], "SPEECH_PROVIDER")
        self.assertTrue(result["integration"]["speechCapabilities"]["stt"])
        self.assertNotIn(secret, json.dumps(result))

        def recognition(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            return ""

        endpoint = f"/api/v1/organizations/{self.organization.public_id}/integrations/{identifier}/test/"
        client = self.client_for_owner()
        # Unit boundary injection only: no HTTP server or live provider claim.
        with patch("chatballs.speech.checking.YandexSTT.recognize_pcm", side_effect=recognition) as provider:
            response = client.post(endpoint)
            self.assertEqual(response.status_code, 200, response.content)
            run, result = self.execute("connections.test.post", {"integration_id": identifier})
            self.assertEqual(provider.call_count, 2)
        self.assertEqual(result["integration"]["status"], "OK")
        with tenant_atomic(self.context):
            self.assertNotIn(secret, json.dumps(NativeEffectReceipt.objects.get(step__run=run).definition))

        def changed_during_io(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            with tenant_atomic(self.context):
                row = Integration.objects.get(pk=identifier)
                row.runtime_revision += 1
                row.save(update_fields=["runtime_revision"])
            return ""

        with patch("chatballs.speech.checking.YandexSTT.recognize_pcm", side_effect=changed_during_io):
            response = client.post(endpoint)
        self.assertEqual(response.status_code, 400, response.content)

    def test_communication_keeps_dictation_and_syncs_voice_mode_for_http_and_native(self):
        _, result = self.execute("connections.post", {"name": "Recording", "provider": "WEB",
            "channelId": self.conversation.channel_id, "config": {"allowedOrigins": ["example.test"],
                "microphoneMode": "dictation", "maxRecordingBytes": 1024, "maxDictationSeconds": 5,
                "answerPlaybackEnabled": True}})
        identifier = result["integration"]["id"]
        self.assertEqual(result["integration"]["config"]["maxDictationSeconds"], 5)
        self.assertTrue(result["integration"]["config"]["answerPlaybackEnabled"])
        self.execute("settings.communication.patch", {"items": [{"id": identifier, "voiceMessages": False}]})
        with tenant_atomic(self.context):
            row = Integration.objects.get(pk=identifier)
            self.assertEqual(row.config["microphoneMode"], "dictation")
        self.execute("connections.detail.patch", {"integration_id": identifier,
            "config": {"microphoneMode": "off"}})
        endpoint = f"/api/v1/organizations/{self.organization.public_id}/company/administration/communication/"
        response = self.client_for_owner().patch(endpoint, {"items": [{"id": identifier, "voiceMessages": True}]}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        with tenant_atomic(self.context):
            row.refresh_from_db()
            self.assertEqual(row.config["microphoneMode"], "voice_message")
        self.execute("settings.communication.patch", {"items": [{"id": identifier, "voiceMessages": False}]})
        _, result = self.execute("connections.get", {})
        self.assertEqual(result["items"][0]["config"]["microphoneMode"], "off")

    def test_synthesis_check_is_explicit_shared_and_outside_transaction(self):
        _, result = self.execute("connections.post", {"name": "Synthesis", "provider": "YANDEX_SPEECHKIT",
            "secret": "SynthesisCredential42", "config": {"folderId": "unit-folder"}})
        identifier = result["integration"]["id"]
        endpoint = f"/api/v1/organizations/{self.organization.public_id}/integrations/{identifier}/test/"

        def synthesis(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            return b"unit-audio"

        with patch("chatballs.speech.providers.yandex_tts.YandexTTS.synthesize", side_effect=synthesis) as provider:
            response = self.client_for_owner().post(endpoint, {"capability": "tts"}, format="json")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["integration"]["ttsCheck"]["status"], "OK")
            _, result = self.execute("connections.test.post", {"integration_id": identifier, "capability": "tts"})
            self.assertEqual(provider.call_count, 2)
        self.assertEqual(result["integration"]["ttsCheck"]["status"], "OK")
        self.assertEqual(result["integration"]["status"], "UNCHECKED")
        self.assertNotIn("SynthesisCredential42", json.dumps(result))

    def test_duplicate_legacy_and_failed_receipts_keep_one_exact_outcome(self):
        run, result = self.execute("groups.get", {})
        action = native_action("groups.get")
        with tenant_atomic(self.context):
            step = run.steps.get()
            receipt = NativeEffectReceipt.objects.get(step=step)
            completed = OperationResult(ResultState.COMPLETED, result)
            self.assertEqual(native_results.save(run, step, action, completed).pk, receipt.pk)
            receipt.definition = {"result": result, "files": []}
            receipt.save()
            self.assertEqual(native_results.save(run, step, action, completed).pk, receipt.pk)
            with self.assertRaises(ExecutionDenied):
                native_results.save(run, step, action, OperationResult(ResultState.FAILED, error_code="permission"))
            receipt.delete()
            failed = OperationResult(ResultState.FAILED, error_code="permission")
            receipt = native_results.save(run, step, action, failed)
            self.assertEqual(native_results.save(run, step, action, failed).pk, receipt.pk)
            self.assertEqual(native_results.restored(receipt).state, ResultState.FAILED)
            receipt.invocation_digest = "wrong-digest"
            receipt.save(update_fields=["invocation_digest"])
            with self.assertRaises(ExecutionDenied):
                native_results.save(run, step, action, failed)
            self.assertEqual(NativeEffectReceipt.objects.filter(step=step).count(), 1)
