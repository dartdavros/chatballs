"""Настройки хранилища файлов в «Настройках» администратора.

GET   company/administration/storage/          — текущее состояние (секреты замаскированы)
PATCH company/administration/storage/          — сохранить; переключение на S3 проверяет доступ
POST  company/administration/storage/check/    — проверить реквизиты (без сохранения)
POST  company/administration/storage/migrate/  — перенести локальные файлы в S3 (worker)

Настройка общая для инстанса: файлы всех организаций лежат в одном месте под
своими префиксами organizations/<public_id>/.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.tenancy import storage_settings as ss

STORAGE_MIGRATION_REQUESTED = "storage.migration_requested"


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:4]}…{value[-2:]}" if len(value) > 8 else "•" * len(value)


def storage_payload(row: ss.StorageSettings) -> dict[str, object]:
    return {
        "backend": row.backend,
        "s3Bucket": row.s3_bucket,
        "s3EndpointUrl": row.s3_endpoint_url,
        "s3Region": row.s3_region,
        "s3AccessKeyMasked": _mask(row.s3_access_key),
        "s3HasSecretKey": bool(row.s3_secret_key),
        "s3AddressingStyle": row.s3_addressing_style or "path",
        "s3Configured": row.s3_configured,
        "s3VerifiedAt": row.s3_verified_at.isoformat() if row.s3_verified_at else None,
        "s3LastError": row.s3_last_error,
        "migration": {
            "status": row.migration_status,
            "total": row.migration_total,
            "done": row.migration_done,
            "error": row.migration_error,
            "startedAt": row.migration_started_at.isoformat() if row.migration_started_at else None,
            "finishedAt": row.migration_finished_at.isoformat() if row.migration_finished_at else None,
        },
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _errors_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        payload = {k: (v[0] if isinstance(v, list) else str(v)) for k, v in error.message_dict.items()}
        detail = next(iter(payload.values()), t("setup.check_fields"))
        return Response({"detail": detail, "errors": payload}, status=400)
    return Response({"detail": "; ".join(error.messages)}, status=400)


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


class StorageSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "settings.view", "PATCH": "company.manage"}

    def get(self, request: Request) -> Response:
        return Response({"storage": storage_payload(ss.StorageSettings.load())})

    def patch(self, request: Request) -> Response:
        row = ss.StorageSettings.load()
        body = request.data
        backend = str(body.get("backend") or row.backend).upper()
        if backend not in ss.StorageBackend.values:
            return Response({"detail": t("settings.unknown_storage_kind"), "errors": {"backend": t("settings.local_or_s3")}}, status=400)
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
        row.backend = backend
        row.updated_by = request.user
        row.save()
        record_audit_event(
            action="administration.storage_updated",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="StorageSettings",
            object_id=str(row.pk),
            payload={"backend": backend, "bucket": row.s3_bucket if backend == ss.StorageBackend.S3 else ""},
            request=request,
        )
        return Response({"storage": storage_payload(row)})


class StorageCheckView(APIView):
    """Проверка реквизитов S3 без сохранения: пробная запись и удаление объекта."""

    permission_classes = [HasCapability]
    required_capability = "company.manage"

    def post(self, request: Request) -> Response:
        row = ss.StorageSettings.load()
        config = _apply_fields(row, request.data)  # строка не сохраняется
        try:
            ss.validate_s3_fields(
                bucket=config.bucket, endpoint_url=config.endpoint_url, region=config.region,
                access_key=config.access_key, secret_key=config.secret_key, addressing_style=config.addressing_style,
            )
            ss.probe_s3(config)
        except ValidationError as error:
            return _errors_response(error)
        return Response({"ok": True})


class StorageMigrateView(APIView):
    """Перенос локальных файлов в S3 — фоновой задачей worker'а."""

    permission_classes = [HasCapability]
    required_capability = "company.manage"

    def post(self, request: Request) -> Response:
        row = ss.StorageSettings.load()
        if row.backend != ss.StorageBackend.S3 or not row.s3_configured:
            return Response({"detail": t("settings.enable_s3_first")}, status=400)
        if row.migration_status == ss.StorageMigrationStatus.RUNNING:
            return Response({"detail": t("settings.migration_running")}, status=409)
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
                payload={"requestedBy": request.user.id},
                tenant_context=request.tenant_context,
            )
        )
        record_audit_event(
            action="administration.storage_migration_requested",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="StorageSettings",
            object_id=str(row.pk),
            request=request,
        )
        return Response({"storage": storage_payload(row)}, status=202)
