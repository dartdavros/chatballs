"""Понятные причины неудачной проверки доступа (SPEC-0037 R-7).

Код причины приходит от адаптера или общего исполнителя и никогда не несёт
текста чужого сервера. Адаптер может описать свои причины («Нет доступа к
CRM»); остальные сводятся к общим текстам.
"""

from __future__ import annotations

from dataclasses import dataclass

from chatballs.i18n import t
from chatballs.integrations.adapters.contracts import AdapterDescriptor, ErrorText

_GENERIC = {
    "unauthorized": "unauthorized",
    "forbidden": "unauthorized",
    "access_expired": "unauthorized",
    "access_revoked": "unauthorized",
    "rate_limited": "rate_limited",
    "temporary": "unreachable",
    "no_response": "unreachable",
    "unreachable": "unreachable",
    "timeout": "unreachable",
    "too_many_redirects": "unreachable",
    "address_internal": "address",
    "address_scheme": "address",
    "address_unresolved": "unreachable",
}


class ServiceCheckFailed(Exception):
    """Проверка доступа не прошла; подключение не создано или не изменено."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ErrorPayload:
    code: str
    title: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "title": self.title, "text": self.text}


def error_payload(adapter: AdapterDescriptor | None, code: str) -> ErrorPayload:
    described = adapter.errors.get(code) if adapter else None
    if described is None:
        generic = _GENERIC.get(code, "rejected")
        described = ErrorText(f"services.error_{generic}_title", f"services.error_{generic}_text")
    return ErrorPayload(code=code, title=t(described.title_key), text=t(described.text_key))
