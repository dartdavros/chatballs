import re

from django.core.exceptions import ValidationError

# Единые правила сложности пароля, зеркалят клиентскую проверку internal-ui.
_LETTER = re.compile(r"[A-Za-zА-Яа-я]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[^A-Za-zА-Яа-я0-9]")


class PasswordComplexityValidator:
    """Require at least one letter, one digit and one special character."""

    def validate(self, password: str, user: object = None) -> None:
        if not _LETTER.search(password):
            raise ValidationError("Пароль должен содержать букву.", code="password_no_letter")
        if not _DIGIT.search(password):
            raise ValidationError("Пароль должен содержать цифру.", code="password_no_digit")
        if not _SPECIAL.search(password):
            raise ValidationError("Пароль должен содержать спецсимвол.", code="password_no_special")

    def get_help_text(self) -> str:
        return "Пароль должен содержать букву, цифру и спецсимвол."
