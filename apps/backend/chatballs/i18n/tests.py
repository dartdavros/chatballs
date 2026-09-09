"""Проверки языка интерфейса.

Главная из них — совпадение наборов ключей в каталогах. Пропущенный перевод не
роняет запрос (строка выходит по-русски), и именно поэтому его легко не
заметить: без теста английский каталог отстаёт молча.
"""

from __future__ import annotations

import pathlib
import re

from django.test import SimpleTestCase, TestCase, override_settings

from chatballs.i18n import normalize_language, parse_accept_language, resolve_language, t
from chatballs.i18n.catalog import _plural_category
from chatballs.i18n.languages import DEFAULT_LANGUAGE, LANGUAGE_CODES
from chatballs.i18n.messages import CATALOG


class CatalogTests(SimpleTestCase):
    def test_every_language_has_the_same_keys(self) -> None:
        russian = set(CATALOG["ru"])
        for code, table in CATALOG.items():
            if code == DEFAULT_LANGUAGE:
                continue
            self.assertEqual(
                russian - set(table), set(), f"нет перевода на {code}"
            )
            self.assertEqual(
                set(table) - russian, set(), f"лишние ключи в {code}"
            )

    def test_placeholders_match_between_languages(self) -> None:
        """Параметры фразы обязаны совпадать: иначе подстановка молча потеряется."""

        placeholders = re.compile(r"\{(\w+)\}")

        def names(message: object) -> set[str]:
            if isinstance(message, dict):
                return {n for form in message.values() for n in placeholders.findall(form)}
            return set(placeholders.findall(str(message)))

        for key, russian in CATALOG["ru"].items():
            for code, table in CATALOG.items():
                if code == DEFAULT_LANGUAGE:
                    continue
                self.assertEqual(
                    names(russian), names(table[key]), f"{key}: расходятся параметры в {code}"
                )

    def test_unknown_key_returns_itself(self) -> None:
        self.assertEqual(t("нет.такого.ключа"), "нет.такого.ключа")

    def test_plural_rule_follows_the_language(self) -> None:
        """Форма выбирается по правилам CLDR, а не по «1 — единственное».

        Строк с числом в каталоге бэкенда сейчас нет, и проверять нечего, кроме
        самого правила: русскому нужны четыре формы, английскому — две, и
        ошибка здесь всплыла бы на первой же фразе со счётчиком.
        """

        self.assertEqual([_plural_category("ru", n) for n in (1, 2, 5, 11, 21)],
                         ["one", "few", "many", "many", "one"])
        self.assertEqual([_plural_category("en", n) for n in (1, 2)], ["one", "other"])


class LanguageResolutionTests(SimpleTestCase):
    def test_normalize_accepts_region_and_case(self) -> None:
        self.assertEqual(normalize_language("ru-RU"), "ru")
        self.assertEqual(normalize_language("EN"), "en")
        self.assertEqual(normalize_language("ru_ru"), "ru")

    def test_unknown_language_is_not_a_choice(self) -> None:
        # Не ошибка, а «выбора нет»: запрос сводится к языку выше по цепочке.
        self.assertEqual(normalize_language("de"), "")
        self.assertEqual(normalize_language(None), "")

    def test_accept_language_respects_quality(self) -> None:
        self.assertEqual(parse_accept_language("en;q=0.9, ru"), "ru")
        self.assertEqual(parse_accept_language("en-GB,en;q=0.9"), "en")
        self.assertEqual(parse_accept_language("de,fr;q=0.5"), "")

    def test_personal_choice_beats_organization(self) -> None:
        self.assertEqual(
            resolve_language(user_language="en", organization_language="ru"), "en"
        )

    def test_organization_beats_installation(self) -> None:
        self.assertEqual(
            resolve_language(organization_language="en", instance_language="ru"), "en"
        )

    def test_browser_is_the_last_resort(self) -> None:
        self.assertEqual(resolve_language(accept_language="en-US"), "en")
        self.assertEqual(resolve_language(), DEFAULT_LANGUAGE)


class FrontendListTests(SimpleTestCase):
    """Список языков продублирован во фронтенде — он обязан совпадать.

    Виджет открывается у клиента до любого запроса к API и знает свой язык сам,
    поэтому список там свой. Расхождение означало бы язык, который интерфейс
    предлагает, а сервер не принимает.
    """

    def test_frontend_language_list_matches(self) -> None:
        source = (
            pathlib.Path(__file__).resolve().parents[4]
            / "packages/shared/src/i18n/index.ts"
        )
        if not source.exists():
            # В образе бэкенда фронтенда нет: проверка имеет смысл только на
            # полном чекауте, где и правят оба списка.
            self.skipTest("фронтенд не смонтирован")
        codes = re.findall(r'\{ code: "(\w+)", label:', source.read_text(encoding="utf-8"))
        self.assertEqual(tuple(codes), LANGUAGE_CODES)


@override_settings(ROOT_URLCONF="chatballs_backend.urls")
class MiddlewareTests(TestCase):
    def test_response_declares_the_language(self) -> None:
        """Ответ помечен языком и Vary: один URL отдаёт разный текст."""

        response = self.client.get("/api/v1/auth/session/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response["Content-Language"], "en")
        self.assertIn("Accept-Language", response["Vary"])
