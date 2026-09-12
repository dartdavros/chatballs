import uuid

from django.conf import settings
from django.db import models

from chatballs.i18n import t
from chatballs.tenancy.models import TenantRelationModel


class CallStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Запрошен"
    RINGING = "RINGING", "Ожидание ответа"
    ACCEPTED = "ACCEPTED", "Принят"
    CONNECTING = "CONNECTING", "Соединение"
    ACTIVE = "ACTIVE", "Активен"
    DECLINED = "DECLINED", "Отклонён"
    CANCELLED = "CANCELLED", "Отменён"
    MISSED = "MISSED", "Пропущен"
    ENDED = "ENDED", "Завершён"
    FAILED = "FAILED", "Ошибка"
    EXPIRED = "EXPIRED", "Истёк"


UNFINISHED_CALL_STATUSES = (
    CallStatus.REQUESTED,
    CallStatus.RINGING,
    CallStatus.ACCEPTED,
    CallStatus.CONNECTING,
    CallStatus.ACTIVE,
)
TERMINAL_CALL_STATUSES = (
    CallStatus.DECLINED,
    CallStatus.CANCELLED,
    CallStatus.MISSED,
    CallStatus.ENDED,
    CallStatus.FAILED,
    CallStatus.EXPIRED,
)


class CallEndedBy(models.TextChoices):
    STAFF = "STAFF", "Сотрудник"
    CUSTOMER = "CUSTOMER", "Клиент"
    SYSTEM = "SYSTEM", t("admin.actor_system")
    TIMEOUT = "TIMEOUT", "Таймаут"


class ParticipantSide(models.TextChoices):
    STAFF = "STAFF", "Сотрудник"
    CUSTOMER = "CUSTOMER", "Клиент"


class ParticipantConnectionState(models.TextChoices):
    PENDING = "PENDING", "Ожидание"
    CONNECTING = "CONNECTING", "Соединение"
    CONNECTED = "CONNECTED", "Подключён"
    RECONNECTING = "RECONNECTING", "Переподключение"
    DISCONNECTED = "DISCONNECTED", "Отключён"
    FAILED = "FAILED", "Ошибка"


class InviteDeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Ожидает доставки"
    SENT = "SENT", "Отправлено"
    FAILED = "FAILED", "Ошибка доставки"


class CallConnectionType(models.TextChoices):
    DIRECT = "DIRECT", "Прямое P2P"
    RELAY = "RELAY", "Через TURN relay"
    UNKNOWN = "UNKNOWN", "Неизвестно"


class CallKind(models.TextChoices):
    AUDIO = "AUDIO", "Аудиозвонок"
    VIDEO = "VIDEO", "Видеозвонок"


class CallSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="call_sessions")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.PROTECT, related_name="call_sessions")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="initiated_calls")
    status = models.CharField(max_length=16, choices=CallStatus.choices, default=CallStatus.REQUESTED, db_index=True)
    kind = models.CharField(max_length=8, choices=CallKind.choices, default=CallKind.AUDIO, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.CharField(max_length=16, choices=CallEndedBy.choices, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    delivery_connection = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.PROTECT,
        related_name="delivered_calls",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(status__in=UNFINISHED_CALL_STATUSES),
                name="uniq_unfinished_call_conversation",
            ),
            models.UniqueConstraint(
                fields=["initiated_by"],
                condition=models.Q(status__in=UNFINISHED_CALL_STATUSES),
                name="uniq_unfinished_call_initiator",
            ),
        ]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:
        return f"call:{self.id}/{self.status}"

    @property
    def duration_seconds(self) -> int | None:
        if self.connected_at is None or self.ended_at is None:
            return None
        return max(0, int((self.ended_at - self.connected_at).total_seconds()))


class CallInvite(TenantRelationModel):
    tenant_relation_fields = ("call_session", "connection_identity")
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_session = models.OneToOneField(CallSession, on_delete=models.CASCADE, related_name="invite")
    connection_identity = models.ForeignKey(
        "conversations.ConnectionIdentity",
        on_delete=models.PROTECT,
        related_name="call_invites",
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(
        max_length=16,
        choices=InviteDeliveryStatus.choices,
        default=InviteDeliveryStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"invite:{self.id}/{self.delivery_status}"


class CallParticipant(TenantRelationModel):
    tenant_relation_fields = ("call_session", "connection_identity")
    call_session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="participants")
    side = models.CharField(max_length=16, choices=ParticipantSide.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="call_participations",
        null=True,
        blank=True,
    )
    connection_identity = models.ForeignKey(
        "conversations.ConnectionIdentity",
        on_delete=models.PROTECT,
        related_name="call_participations",
        null=True,
        blank=True,
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    last_connection_state = models.CharField(
        max_length=16,
        choices=ParticipantConnectionState.choices,
        default=ParticipantConnectionState.PENDING,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["call_session", "side"], name="uniq_call_participant_side"),
            models.CheckConstraint(
                condition=(
                    models.Q(side=ParticipantSide.STAFF, user__isnull=False, connection_identity__isnull=True)
                    | models.Q(side=ParticipantSide.CUSTOMER, user__isnull=True, connection_identity__isnull=False)
                ),
                name="call_participant_identity_matches_side",
            ),
        ]

    def __str__(self) -> str:
        return f"participant:{self.call_session_id}/{self.side}"


class CallMetric(TenantRelationModel):
    """Технические метрики соединения без медиаконтента (SPEC-CHATBALLS-0013 §13).

    Хранится только КАТЕГОРИЯ ICE-кандидата (host/srflx/prflx/relay) и RTT, но
    никогда сам ICE candidate, его адрес, SDP или медиапоток. Позволяет считать
    долю direct/relay звонков (E15) и подтверждать TURN fallback, не раскрывая
    сетевые адреса участников.
    """

    tenant_relation_fields = ("call_session",)

    call_session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="metrics")
    side = models.CharField(max_length=16, choices=ParticipantSide.choices)
    connection_type = models.CharField(
        max_length=16,
        choices=CallConnectionType.choices,
        default=CallConnectionType.UNKNOWN,
    )
    local_candidate_type = models.CharField(max_length=8, blank=True)
    remote_candidate_type = models.CharField(max_length=8, blank=True)
    round_trip_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["call_session", "side"], name="uniq_call_metric_side"),
        ]

    def __str__(self) -> str:
        return f"metric:{self.call_session_id}/{self.side}/{self.connection_type}"
