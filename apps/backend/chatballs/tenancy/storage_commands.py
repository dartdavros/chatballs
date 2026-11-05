"""Storage administration shared by HTTP and global native actions."""
from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.integrations.action_catalog.authority import require_instance
from chatballs.tenancy import storage_settings as ss
from chatballs.tenancy.storage_payloads import storage_payload

STORAGE_MIGRATION_REQUESTED = "storage.migration_requested"

def _errors_response(error: ValidationError) -> CommandOutcome:
    if hasattr(error, "message_dict"):
        payload = {k: (v[0] if isinstance(v, list) else str(v)) for k, v in error.message_dict.items()}
        detail = next(iter(payload.values()), t("setup.check_fields"))
        return CommandOutcome({"detail": detail, "errors": payload}, status=400)
    return CommandOutcome({"detail": "; ".join(error.messages)}, status=400)


def _apply_fields(row: ss.StorageSettings, body: dict) -> ss.StorageConfig:
    """Накладывает поля запроса на строку (пустые секреты = оставить прежние)."""
    if "s3Bucket" in body:
        row.s3_bucket = str(body.get("s3Bucket") or "").strip()
    if "s3EndpointUrl" in body:
        row.s3_endpoint_url = str(body.get("s3EndpointUrl") or "").strip().rstrip("/")
    if "s3Region" in body:
        row.s3_region = str(body.get("s3Region") or "").strip()
    if "s3AddressingStyle" in body:
        row.s3_addressing_style = str(body.get("s3AddressingStyle") or "path").strip() or "path"
    if body.get("s3AccessKey"):
        row.s3_access_key = str(body["s3AccessKey"]).strip()
    if body.get("s3SecretKey"):
        row.s3_secret_key = str(body["s3SecretKey"]).strip()
    return ss.config_from_settings(row)


def read(user):
    require_instance(user, read=True)
    return CommandOutcome({"storage": storage_payload(ss.StorageSettings.load())})


def update(user, body, *, request=None):
    user = require_instance(user)
    row = ss.StorageSettings.load()
    expected_revision = row.updated_at
    body = body if isinstance(body, dict) else {}
    backend = str(body.get("backend") or row.backend).upper()
    if backend not in ss.StorageBackend.values:
        return CommandOutcome({"detail": t("settings.unknown_storage_kind"), "errors": {"backend": t("settings.local_or_s3")}}, status=400)
    config = _apply_fields(row, body)
    if backend == ss.StorageBackend.S3:
        try:
            ss.validate_s3_fields(
                bucket=row.s3_bucket, endpoint_url=row.s3_endpoint_url, region=row.s3_region,
                access_key=row.s3_access_key, secret_key=row.s3_secret_key, addressing_style=row.s3_addressing_style,
            )
            ss.probe_s3(ss.StorageConfig(**{**config.__dict__, "backend": ss.StorageBackend.S3}))
        except ValidationError as error:
            return _errors_response(error)
        row.s3_last_error = ""
        from django.utils import timezone

        row.s3_verified_at = timezone.now()
    with transaction.atomic():
        user = require_instance(user)
        current = ss.StorageSettings.objects.select_for_update().get(pk=row.pk)
        if current.updated_at != expected_revision:
            return CommandOutcome({"detail": t("native.instance.settings_changed")}, status=409)
        fields = ("s3_bucket", "s3_endpoint_url", "s3_region", "s3_access_key", "s3_secret_key",
                  "s3_addressing_style", "s3_last_error", "s3_verified_at")
        for name in fields:
            setattr(current, name, getattr(row, name))
        current.backend = backend
        current.updated_by = user
        current.save(update_fields=[*fields, "backend", "updated_by", "updated_at"])
        record_audit_event(action="administration.storage_updated", actor=user, organization=None,
            object_type="StorageSettings", object_id=str(current.pk),
            payload={"backend": backend, "bucket": current.s3_bucket if backend == ss.StorageBackend.S3 else ""},
            request=request)
        return CommandOutcome({"storage": storage_payload(current)})



def check(user, body, *, request=None):
    user = require_instance(user)
    row = ss.StorageSettings.load()
    config = _apply_fields(row, body)  # строка не сохраняется
    try:
        ss.validate_s3_fields(
            bucket=config.bucket, endpoint_url=config.endpoint_url, region=config.region,
            access_key=config.access_key, secret_key=config.secret_key, addressing_style=config.addressing_style,
        )
        ss.probe_s3(config)
    except ValidationError as error:
        return _errors_response(error)
    return CommandOutcome({"ok": True})


@transaction.atomic
def migrate(user, *, request=None):
    user = require_instance(user)
    row = ss.StorageSettings.load()
    row = ss.StorageSettings.objects.select_for_update().get(pk=row.pk)
    if row.backend != ss.StorageBackend.S3 or not row.s3_configured:
        return CommandOutcome({"detail": t("settings.enable_s3_first")}, status=400)
    if row.migration_status == ss.StorageMigrationStatus.RUNNING:
        return CommandOutcome({"detail": t("settings.migration_running")}, status=409)
    row.migration_status = ss.StorageMigrationStatus.RUNNING
    row.migration_total = 0
    row.migration_done = 0
    row.migration_error = ""
    from django.utils import timezone

    row.migration_started_at = timezone.now()
    row.migration_finished_at = None
    row.save()
    enqueue_event(
        DomainEvent(
            aggregate_type="StorageSettings",
            aggregate_id=str(row.pk),
            event_type=STORAGE_MIGRATION_REQUESTED,
            payload={"requestedBy": user.id},
            tenant_context=None,
        )
    )
    record_audit_event(
        action="administration.storage_migration_requested",
        actor=user,
        organization=None,
        object_type="StorageSettings",
        object_id=str(row.pk),
        request=request,
    )
    return CommandOutcome({"storage": storage_payload(row)}, status=202)
