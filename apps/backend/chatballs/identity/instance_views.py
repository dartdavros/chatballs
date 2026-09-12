"""Адрес установки в «Настройках».

Мастер первого запуска запоминает адрес, на котором его открыли. Дальше владелец
меняет его здесь — когда завёл домен и поставил перед установкой TLS. Никаких
переменных окружения: адрес живёт в настройках инсталляции и из него строятся
внешние ссылки (вложения знаний, файлы статей, приглашения на звонок).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.i18n.languages import DEFAULT_LANGUAGE, LANGUAGES, normalize_language
from chatballs.identity.instance_settings import (
    InstanceSettings,
    email_connection,
    email_from_address,
    invalidate_cache,
    public_base_url,
)
from chatballs.support_portals.addressing import normalize_domain, validate_domain

SCHEMES = ("http", "https")


def instance_payload(row: InstanceSettings) -> dict:
    return {
        "publicHost": row.public_host,
        "publicScheme": row.public_scheme or "http",
        "publicUrl": public_base_url(),
        # Язык экранов, где организации ещё нет: логин, сброс пароля, мастер.
        "defaultLanguage": row.default_language or DEFAULT_LANGUAGE,
        "languages": [{"code": code, "label": label} for code, label in LANGUAGES],
        "updatedAt": row.updated_at,
        "email": {
            "host": row.email_host,
            "port": row.email_port,
            "user": row.email_user,
            # Пароль наружу не возвращается: пустое поле при сохранении
            # означает «оставить прежний».
            "hasPassword": bool(row.email_password),
            "useTls": row.email_use_tls,
            "from": row.email_from,
            "configured": bool(row.email_host),
        },
        "turn": {
            # Секрет общий с coturn и лежит в томе секретов: наружу не отдаём
            # и в настройках не показываем — вводить его человеку не нужно.
            "urls": [line for line in row.turn_urls.splitlines() if line.strip()],
            "ttlSeconds": row.turn_ttl_seconds,
            "secretReady": bool(settings.CHATBALLS_CALL_TURN_SECRET),
        },
    }


class InstanceAddressView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "settings.view", "PATCH": "company.manage"}

    def get(self, request: Request) -> Response:
        return Response({"instance": instance_payload(InstanceSettings.load())})

    def patch(self, request: Request) -> Response:
        row = InstanceSettings.load()
        body = request.data if isinstance(request.data, dict) else {}
        errors: dict[str, str] = {}

        # Владелец может вставить и целый URL из адресной строки — берём хост.
        raw_host = str(body.get("publicHost", row.public_host)).strip()
        if "//" in raw_host:
            raw_host = raw_host.split("//", 1)[1]
        host = normalize_domain(raw_host.split("/", 1)[0].split(":", 1)[0])
        if not host:
            errors["publicHost"] = t("settings.address_required")
        else:
            try:
                # IP-адрес — обычный случай коробки: домена может не быть вовсе.
                if not _looks_like_ipv4(host):
                    validate_domain(host)
            except ValidationError:
                errors["publicHost"] = t("settings.invalid_address")

        scheme = str(body.get("publicScheme", row.public_scheme or "http")).lower()
        if scheme not in SCHEMES:
            errors["publicScheme"] = t("settings.http_or_https")

        raw_language = str(body.get("defaultLanguage", row.default_language)).strip()
        language = normalize_language(raw_language)
        if raw_language and not language:
            errors["defaultLanguage"] = t("settings.language_unsupported")

        if errors:
            return Response(
                {"detail": next(iter(errors.values())), "errors": errors}, status=400
            )

        fields = [
            "public_host",
            "public_scheme",
            "previous_public_host",
            "default_language",
            "updated_at",
        ]
        if host != row.public_host:
            # Прежний адрес остаётся принятым: владелец меняет адрес заранее,
            # сидя на старом, и не должен выпасть из установки в тот же миг.
            row.previous_public_host = row.public_host
        row.public_host = host
        row.public_scheme = scheme
        row.default_language = language or DEFAULT_LANGUAGE

        email = body.get("email")
        if isinstance(email, dict):
            row.email_host = str(email.get("host", row.email_host)).strip()
            row.email_user = str(email.get("user", row.email_user)).strip()
            row.email_from = str(email.get("from", row.email_from)).strip()
            row.email_use_tls = bool(email.get("useTls", row.email_use_tls))
            try:
                row.email_port = int(email.get("port", row.email_port))
            except (TypeError, ValueError):
                return Response(
                    {"detail": t("settings.port_is_number"), "errors": {"emailPort": t("settings.port_is_number")}},
                    status=400,
                )
            # Пустой пароль означает «оставить прежний»: наружу он не отдаётся.
            password = str(email.get("password", ""))
            if password:
                row.email_password = password
            fields += [
                "email_host",
                "email_port",
                "email_user",
                "email_password",
                "email_use_tls",
                "email_from",
            ]

        turn = body.get("turn")
        if isinstance(turn, dict):
            urls = turn.get("urls", [])
            if isinstance(urls, list):
                row.turn_urls = sep_join(urls)
            try:
                row.turn_ttl_seconds = max(60, int(turn.get("ttlSeconds", row.turn_ttl_seconds)))
            except (TypeError, ValueError):
                return Response(
                    {"detail": t("settings.ttl_is_seconds"),
                     "errors": {"turnTtlSeconds": t("settings.seconds_number")}},
                    status=400,
                )
            fields += ["turn_urls", "turn_ttl_seconds"]

        row.save(update_fields=fields)
        invalidate_cache()
        return Response({"instance": instance_payload(row)})


def _looks_like_ipv4(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)


class InstanceEmailCheckView(APIView):
    """Проверка почты: отправить письмо себе и увидеть ошибку сразу.

    Без этого владелец узнаёт о неверном SMTP только тогда, когда сотрудник не
    получил приглашение.
    """

    permission_classes = [HasCapability]
    required_capability = "company.manage"

    def post(self, request: Request) -> Response:
        from django.core.mail import send_mail

        connection = email_connection()
        if connection is None:
            return Response(
                {"detail": t("settings.smtp_required_first")}, status=400
            )
        recipient = str(request.data.get("email", "")).strip() or request.user.email
        try:
            send_mail(
                subject=t("settings.mail_test_subject"),
                message=t("settings.mail_test_body"),
                from_email=email_from_address(),
                recipient_list=[recipient],
                connection=connection,
            )
        except Exception as error:  # ошибки SMTP разнообразны — показываем текст
            return Response({"detail": str(error)[:300]}, status=400)
        return Response({"sent": recipient})


def sep_join(urls) -> str:
    """Адреса TURN хранятся строками: по одному на строку."""

    lines = [str(item).strip() for item in urls if str(item).strip()]
    return chr(10).join(lines)
