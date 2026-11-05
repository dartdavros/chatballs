"""Проверка STT настоящим запросом без удержания tenant-транзакции."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.utils import timezone

from chatballs.i18n import customer_language, t
from chatballs.integrations.models import Integration
from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_stt import YandexSTT


@dataclass(frozen=True, slots=True)
class SpeechCheck:
    integration_id: int
    revision: int
    api_key: str
    folder_id: str
    language: str
    model: str


def prepare_check(integration) -> SpeechCheck:
    return SpeechCheck(
        integration.id, integration.runtime_revision, integration.secret,
        integration.config.get("folder_id", ""),
        {"ru": "ru-RU", "en": "en-US"}.get(customer_language(integration.organization), ""),
        integration.config.get("transcription_model") or "general",
    )


def run_check(job: SpeechCheck) -> str:
    try:
        # 100 мс тишины проверяют настоящий v3 STT; пустая речь здесь ожидаема.
        YandexSTT(api_key=job.api_key, folder_id=job.folder_id, language=job.language).recognize_pcm(
            bytes(3200), model=job.model,
        )
        return ""
    except SpeechError as error:
        return error.code


def finish_check(context, job: SpeechCheck, error_code: str):
    integration = Integration.objects.select_for_update().get(
        id=job.integration_id, organization_id=context.organization_id, provider="YANDEX_SPEECHKIT",
    )
    if integration.runtime_revision != job.revision:
        raise ValidationError({"integration": t("speech.check_outdated")})
    integration.status = "ERROR" if error_code else "OK"
    integration.last_error = t(f"speech.{error_code}") if error_code else ""
    integration.last_error_code = error_code
    integration.last_checked_at = timezone.now()
    if not error_code:
        integration.runtime_revision += 1
    integration.save(update_fields=["status", "last_error", "last_error_code", "last_checked_at", "runtime_revision", "updated_at"])
    return integration
