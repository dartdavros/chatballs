"""Публичная конфигурация веб-виджета."""

from chatballs.i18n import t
from chatballs.i18n.languages import resolve_language
from chatballs.identity.instance_settings import default_language
from chatballs.integrations.features import features_payload
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.appearance import public_appearance
from chatballs.webchat.consent_html import clean_consent_html
from chatballs.webchat.models import WebChatWidget
from chatballs.webchat.pre_chat import pre_chat_payload
from chatballs.webchat.recording_configuration import public_recording
from chatballs.webchat.sessions import origin_allowed
from chatballs.webchat.site_event_config import public_rule


def public_config(*, context: TenantContext, widget: WebChatWidget, origin: str) -> dict:
    integration = widget.integration
    # Язык отдаётся и тогда, когда виджет открыть нельзя: «Чат временно
    # недоступен» — это организация говорит со своим клиентом, и говорить она
    # должна на своём языке, а не на языке браузера посетителя.
    language = resolve_language(
        organization_language=context.organization.language,
        instance_language=default_language(),
    )
    if integration.channel_id is None:
        return {"available": False, "language": language}
    if not origin_allowed(widget, origin):
        return {"available": False, "reason": "domain", "language": language}
    cfg = widget.presentation_config
    consent = widget.consent_config
    channel = integration.channel
    fallback = []
    for sib in Integration.objects.filter(channel=channel).exclude(id=integration.id):
        username = sib.config.get("bot_username")
        if sib.provider == IntegrationProvider.TELEGRAM and username:
            fallback.append({"label": t("webchat.write_in_telegram"), "url": f"https://t.me/{username}"})
        elif sib.provider == IntegrationProvider.MAX and username:
            fallback.append({"label": t("webchat.write_in_max"), "url": ""})
    appearance = public_appearance(cfg)
    recording = public_recording(integration)
    from chatballs.speech.synthesis import public_synthesis

    recording.update(public_synthesis(integration))
    consent_text = clean_consent_html(str(consent.get("consent_text") or "")) or t("webchat.default_consent", language=language)
    if integration.config.get("answerPlaybackEnabled", False):
        consent_text += "<p>" + t("speech.consent_disclosure", language=language) + "</p>"
    return {
        "available": True,
        "autonomous": _autonomous(integration),
        "widgetKey": widget.public_key,
        # Язык обвязки виджета — язык организации: на нём отвечают и агент, и
        # оператор, и английская кнопка «Send» вокруг русских ответов выглядела
        # бы ошибкой.
        "language": language,
        # Что разрешено в этой точке входа: виджет прячет микрофон при запрете.
        "features": {**features_payload(integration), "voiceMessages": recording["microphoneMode"] == "voice_message"},
        "speech": recording,
        "title": cfg.get("title") or channel.name,
        "accent": appearance["accent"],
        "appearance": appearance,
        "greeting": cfg.get("greeting") or t("webchat.default_greeting", language=language),
        "consent": {
            # Запись могла сохраниться до очистки — наружу уходит только
            # безопасная разметка (SPEC-0020 R-15).
            "text": consent_text,
            "version": consent.get("consent_version") or "v1",
        },
        "quickReplies": cfg.get("quick_replies") or [],
        # Схема своих полей — уже без «Видит AI» (widgets.ensure_widget).
        "fields": cfg.get("fields") or [],
        "preChat": pre_chat_payload(integration.config),
        "siteEvent": public_rule(integration),
        "fallback": fallback,
    }




def _autonomous(integration):
    from chatballs.identity.operation_modes import autonomous_allowed

    return autonomous_allowed(integration.channel, organization=integration.organization, connection=integration)
