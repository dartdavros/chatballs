"""Валидация речевого подключения без сетевого I/O."""

import re

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.speech.contracts import SPEECHKIT_MODELS


def normalize_speechkit(config: dict) -> dict:
    folder = config.get("folderId", config.get("folder_id", ""))
    model = config.get("transcriptionModel", config.get("transcription_model", ""))
    if not isinstance(folder, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", folder.strip()):
        raise ValidationError({"folderId": t("speech.folder_required")})
    if not isinstance(model, str) or (model and model not in SPEECHKIT_MODELS):
        raise ValidationError({"transcriptionModel": t("speech.model_unsupported")})
    return {"folder_id": folder.strip(), "transcription_model": model}
