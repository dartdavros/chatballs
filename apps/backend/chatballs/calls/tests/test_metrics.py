import uuid

from chatballs.calls import signaling
from chatballs.calls.models import CallConnectionType, CallMetric, ParticipantSide
from chatballs.calls.serializers import call_payload
from chatballs.calls.services import record_call_metric
from chatballs.calls.tests.helpers import CallTestCase, create_call_request
from chatballs.testing import system_tenant_context


class RecordCallMetricTests(CallTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.call = create_call_request(
            conversation_id=self.conversation.id, initiator=self.owner
        ).call_session

    def _record(self, **kwargs):
        record_call_metric(
            context=system_tenant_context(self.organization),
            call_session_id=self.call.id,
            side=ParticipantSide.STAFF,
            **kwargs,
        )
        return CallMetric.objects.get(call_session=self.call, side=ParticipantSide.STAFF)

    def test_direct_connection_type_from_non_relay_candidates(self) -> None:
        metric = self._record(local_candidate_type="host", remote_candidate_type="srflx", round_trip_ms=42)
        self.assertEqual(metric.connection_type, CallConnectionType.DIRECT)
        self.assertEqual(metric.local_candidate_type, "host")
        self.assertEqual(metric.round_trip_ms, 42)

    def test_relay_candidate_marks_turn_fallback(self) -> None:
        metric = self._record(local_candidate_type="relay", remote_candidate_type="srflx")
        self.assertEqual(metric.connection_type, CallConnectionType.RELAY)

    def test_unknown_when_no_candidate_types(self) -> None:
        metric = self._record(local_candidate_type=None, remote_candidate_type=None)
        self.assertEqual(metric.connection_type, CallConnectionType.UNKNOWN)

    def test_invalid_candidate_type_is_dropped(self) -> None:
        # Клиент прислал мусор/адрес — храним только валидную категорию (RFC 8445).
        metric = self._record(local_candidate_type="203.0.113.7", remote_candidate_type="RELAY")
        self.assertEqual(metric.local_candidate_type, "")
        self.assertEqual(metric.remote_candidate_type, "relay")
        self.assertEqual(metric.connection_type, CallConnectionType.RELAY)

    def test_round_trip_ms_sanitized(self) -> None:
        self.assertEqual(self._record(round_trip_ms=-5).round_trip_ms, 0)
        self.assertEqual(self._record(round_trip_ms=10**9).round_trip_ms, 60_000)
        self.assertEqual(self._record(round_trip_ms=12.9).round_trip_ms, 12)
        self.assertIsNone(self._record(round_trip_ms=True).round_trip_ms)
        self.assertIsNone(self._record(round_trip_ms="fast").round_trip_ms)

    def test_upsert_is_idempotent_per_side(self) -> None:
        self._record(local_candidate_type="host")
        self._record(local_candidate_type="relay")
        metrics = CallMetric.objects.filter(call_session=self.call, side=ParticipantSide.STAFF)
        self.assertEqual(metrics.count(), 1)
        self.assertEqual(metrics.first().connection_type, CallConnectionType.RELAY)

    def test_unknown_side_ignored(self) -> None:
        record_call_metric(
            context=system_tenant_context(self.organization),
            call_session_id=self.call.id,
            side="ALIEN",
            local_candidate_type="host",
        )
        self.assertFalse(CallMetric.objects.filter(call_session=self.call).exists())

    def test_missing_call_ignored(self) -> None:
        record_call_metric(
            context=system_tenant_context(self.organization),
            call_session_id=uuid.uuid4(),
            side=ParticipantSide.STAFF,
            local_candidate_type="host",
        )
        self.assertEqual(CallMetric.objects.count(), 0)

    def test_signaling_helper_maps_camel_case_payload(self) -> None:
        signaling.record_metric(
            system_tenant_context(self.organization),
            self.call.id,
            ParticipantSide.CUSTOMER,
            {"localCandidateType": "relay", "remoteCandidateType": "host", "roundTripMs": 88},
        )
        metric = CallMetric.objects.get(call_session=self.call, side=ParticipantSide.CUSTOMER)
        self.assertEqual(metric.connection_type, CallConnectionType.RELAY)
        self.assertEqual(metric.round_trip_ms, 88)

    def test_call_payload_exposes_metrics(self) -> None:
        self._record(local_candidate_type="host", remote_candidate_type="host", round_trip_ms=15)
        payload = call_payload(self.call)
        self.assertEqual(len(payload["metrics"]), 1)
        entry = payload["metrics"][0]
        self.assertEqual(entry["side"], ParticipantSide.STAFF)
        self.assertEqual(entry["connectionType"], CallConnectionType.DIRECT)
        self.assertEqual(entry["roundTripMs"], 15)
