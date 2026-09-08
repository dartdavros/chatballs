import re
from contextvars import ContextVar
from uuid import uuid4

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# Значение приходит заголовком запроса и ложится в CharField(max_length=128)
# записи аудита и очереди событий. Без ограничения строка длиннее валила
# запись в БД — а первым это ловил публичный /auth/login/, где аудит пишется
# на каждую неудачную попытку: вместо 401 приходило 500, и след входа
# терялся. Оставляем печатный ASCII: значение идёт и в строку лога, и в
# заголовок ответа.
_MAX_LENGTH = 128
_UNSAFE = re.compile(r"[^A-Za-z0-9._:@/+-]")


def sanitize_correlation_id(value: str | None) -> str:
    """Пригодный для хранения и логов идентификатор; мусор — в пустую строку."""
    return _UNSAFE.sub("", str(value or ""))[:_MAX_LENGTH]


def ensure_correlation_id(value: str | None = None) -> str:
    correlation_id = sanitize_correlation_id(value) or str(uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str:
    return correlation_id_var.get() or ensure_correlation_id()
