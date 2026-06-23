import re

# Минимизация данных перед LLM (ADR-HUB-0011): email, телефоны, длинные
# числовые идентификаторы (карты/платежи/заказы) не передаются в модель.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_DIGITS = re.compile(r"\b\d[\d\s-]{10,}\d\b")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")


def redact(text: str) -> str:
    if not text:
        return text
    text = _EMAIL.sub("[email]", text)
    text = _LONG_DIGITS.sub("[number]", text)
    text = _PHONE.sub("[phone]", text)
    return text
