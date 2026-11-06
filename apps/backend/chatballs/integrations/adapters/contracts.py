"""Контракт адаптера сервиса (SPEC-0037 R-3, R-4, R-6; C4 code-service-adapter-contract).

Описание — неизменяемые dataclass: адаптер собирает их при импорте модуля, а
реестр проверяет до того, как хоть одно подключение их увидит. Тексты —
ключи каталога i18n: язык выбирается на каждый запрос, а не при импорте.

Обработчики получают ``OperationContext``, собранный сервером: организацию,
подключение, расшифрованные на время вызова credentials, ключ эффекта и срок.
Браузер и модель их не назначают.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from chatballs.integrations.adapters.initial_values import InitialValue
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.adapters.templates import ScenarioTemplate as ScenarioTemplate
from chatballs.integrations.adapters.templates import TemplateStep as TemplateStep

if TYPE_CHECKING:
    from chatballs.integrations.adapters.references import EntityReferences
    from chatballs.integrations.adapters.synchronization import SynchronizationBinding
    from chatballs.integrations.models import Integration


class Effect(StrEnum):
    READ = "read"
    SEARCH = "search"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BATCH = "batch"
    OTHER = "other"


# Эффекты, которые не меняют данные внешней системы.
READ_EFFECTS = frozenset({Effect.READ, Effect.SEARCH})


class Mode(StrEnum):
    SYNC = "sync"
    # Долгая операция: ответ сервиса — продолжение, итог приходит позже.
    LONG = "long"


class RetryStrategy(StrEnum):
    # Сервис принимает ключ идемпотентности: повтор с тем же ключом безопасен.
    IDEMPOTENCY_KEY = "idempotency_key"
    # Результат устанавливается сверкой (reconcile) по ключу эффекта.
    RECONCILE = "reconcile"
    # Операция только читает: повтор не меняет данных.
    SAFE_READ = "safe_read"
    # Определить исход после сбоя нельзя: остаётся «Результат неизвестен».
    NONE = "none"


class Delivery(StrEnum):
    WEBHOOK = "webhook"
    CALLBACK = "callback"
    POLL = "poll"


class ResultState(StrEnum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"
    UNKNOWN = "unknown"
    DECISION = "decision"


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 30.0
    max_response_bytes: int = 256 * 1024
    # Больше этого бинарный/большой ответ не принимается даже в файл.
    max_file_bytes: int = 25 * 1024 * 1024


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class FileRef:
    file_id: str
    name: str
    content_type: str
    size: int


@dataclass(frozen=True)
class OperationContext:
    organization_id: int
    connection: Integration
    settings: dict[str, Any]
    credentials: dict[str, Any]
    effect_key: str = ""
    run_id: str = ""
    step_path: str = ""
    deadline_seconds: float | None = None
    causal_chain: tuple[str, ...] = ()
    # Расширение авторизации способа доступа и его параметры (auth.py).
    auth: Any = None
    auth_options: dict[str, Any] = field(default_factory=dict)
    # Транспорт (transport.py) и хранилище файлов операции (files.py).
    transport: Any = None
    store_file: Callable[..., FileRef] | None = None
    # fileId → (имя, тип, байты) файла этой организации.
    open_file: Callable[[str], tuple[str, str, bytes]] | None = None


@dataclass(frozen=True)
class OperationResult:
    state: ResultState
    data: Any = None
    files: tuple[FileRef, ...] = ()
    external_reference: str = ""
    # Что нужно для resume/reconcile/cancel долгой операции.
    continuation: dict[str, Any] = field(default_factory=dict)
    # Безопасный код причины, без текста чужого сервера и секретов.
    error_code: str = ""
    retry_after_seconds: float | None = None
    correlation: str = ""
    event_key: str = ""
    deadline: datetime | None = None


Execute = Callable[[OperationContext, "OperationDescriptor", dict[str, Any]], OperationResult]
Continue = Callable[[OperationContext, "OperationDescriptor", dict[str, Any]], OperationResult]


@dataclass(frozen=True)
class OperationHandlers:
    execute: Execute | None = None
    resume: Continue | None = None
    reconcile: Continue | None = None
    cancel: Continue | None = None


@dataclass(frozen=True)
class OperationDescriptor:
    key: str
    title_key: str
    effect: Effect
    input: TypeSpec
    output: TypeSpec
    handlers: OperationHandlers
    description_key: str = ""
    mode: Mode = Mode.SYNC
    retry: RetryStrategy = RetryStrategy.NONE
    cancellable: bool = False
    # Область доступа сервиса, которая нужна операции (например, «crm»).
    permission_scope: str = ""
    limits: Limits = DEFAULT_LIMITS
    # Произвольные данные протокола для общего HTTP/MCP-исполнителя.
    protocol: dict[str, Any] = field(default_factory=dict)
    entity_kind: str = ""
    # Only the manual create form consumes these; execution never merges them.
    initial_values: tuple[InitialValue, ...] = ()


@dataclass(frozen=True)
class EventDescriptor:
    key: str
    title_key: str
    payload: TypeSpec
    delivery: Delivery
    ingress: Callable[..., Any] | None = None
    poll: Callable[..., Any] | None = None
    replay_seconds: int | None = None


@dataclass(frozen=True)
class LookupItem:
    value: str | int
    label: str


@dataclass(frozen=True)
class LookupDescriptor:
    key: str
    title_key: str
    # Справочник загружается операцией чтения адаптера.
    operation: str
    # Как из результата операции получить пункты справочника.
    items: Callable[[Any], list[LookupItem]]
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorText:
    title_key: str
    text_key: str


@dataclass(frozen=True)
class CheckDescriptor:
    """Проверка доступа: только операцией чтения, без бизнес-изменений (R-7)."""

    operation: str
    note_key: str
    # Входы проверки, которые вводит администратор (например, ID записи).
    inputs: TypeSpec | None = None
    # Код ошибки по результату чтения или None, если доступ достаточен.
    interpret: Callable[[OperationResult], str | None] | None = None


@dataclass(frozen=True)
class AuthMethod:
    key: str
    # Расширение авторизации из реестра: «ключ@версия».
    extension: str
    title_key: str
    fields: TypeSpec
    about_key: str = ""
    note_key: str = ""
    # Как способ доступа называется в карточке подключения.
    access_label_key: str = ""
    # Что сохранено, для строки состояния карточки («Ссылка сохранена»).
    saved_label_key: str = ""
    check: CheckDescriptor | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HelpBlock:
    title_key: str
    steps: tuple[str, ...] = ()
    paragraphs: tuple[str, ...] = ()
    link_key: str = ""
    # Адрес инструкции зависит от языка, поэтому тоже ключ каталога.
    link_url_key: str = ""


@dataclass(frozen=True)
class Presentation:
    title_key: str
    about_key: str
    connect_lead_key: str
    # Файлы логотипа рядом с модулем адаптера: для светлой и тёмной темы.
    logo_light: str
    logo_dark: str
    host_label_key: str
    help: HelpBlock | None = None


@dataclass(frozen=True)
class EntityDescriptor:
    key: str
    title_key: str
    fields: TypeSpec
    native_entities: tuple[str, ...] = ()
    synchronization: SynchronizationBinding | None = None
    references: EntityReferences | None = None


@dataclass(frozen=True)
class Unsupported:
    capability: str
    reason_key: str


@dataclass(frozen=True)
class AdapterDescriptor:
    key: str
    contract_version: int
    presentation: Presentation
    auth_methods: tuple[AuthMethod, ...]
    operations: tuple[OperationDescriptor, ...]
    settings: TypeSpec = TypeSpec("object")
    events: tuple[EventDescriptor, ...] = ()
    lookups: tuple[LookupDescriptor, ...] = ()
    templates: tuple[ScenarioTemplate, ...] = ()
    unsupported: tuple[Unsupported, ...] = ()
    errors: dict[str, ErrorText] = field(default_factory=dict)
    # Показывать ли в каталоге. Служебные адаптеры (мост старых HTTP/MCP)
    # работают через реестр, но пользователь их не подключает.
    listed: bool = True
    # Каталог модуля адаптера: от него берутся файлы логотипа.
    package_dir: str = ""
    transport: str = "https@1"
    entities: tuple[EntityDescriptor, ...] = ()

    def operation(self, key: str) -> OperationDescriptor | None:
        return next((item for item in self.operations if item.key == key), None)

    def auth_method(self, key: str) -> AuthMethod | None:
        return next((item for item in self.auth_methods if item.key == key), None)

    def lookup(self, key: str) -> LookupDescriptor | None:
        return next((item for item in self.lookups if item.key == key), None)
