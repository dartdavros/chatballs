"""Поиск по переписке на обоих языках идёт одной конфигурацией — «russian».

Выглядит как недосмотр: англоязычная установка ищет по своим письмам русской
конфигурацией. На деле «russian» в PostgreSQL — не «русский стеммер на всё», а
карта по типу токена: латиница уходит в english_stem, кириллица — в
russian_stem. То есть английские слова уже стеммятся английским стеммером.

Обратное неверно, и это здесь же проверяется: «english» отдаёт кириллицу
english_stem и оставляет её без основы. Поэтому второй индекс под английский не
нужен, а замена конфигурации на «english» была бы регрессом для русской
переписки. Тест стоит затем, чтобы это не «починили» ещё раз.
"""

from __future__ import annotations

from django.db import connection
from django.test import TestCase

from chatballs.conversations.models import Message


class SearchConfigTests(TestCase):
    def _matches(self, config: str, text: str, query: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_tsvector(%s, %s) @@ websearch_to_tsquery(%s, %s)",
                [config, text, config, query],
            )
            return cursor.fetchone()[0]

    def test_russian_config_stems_english_words(self) -> None:
        self.assertTrue(self._matches("russian", "the deliveries arrived", "delivery"))
        self.assertTrue(self._matches("russian", "we are shipping orders", "shipped"))

    def test_russian_config_stems_russian_words(self) -> None:
        self.assertTrue(self._matches("russian", "заказы доставлены", "заказ"))

    def test_english_config_leaves_russian_words_unstemmed(self) -> None:
        # Ровно причина, по которой конфигурация не переключается по языку
        # организации: на английской конфигурации «заказы» не находит «заказ».
        self.assertFalse(self._matches("english", "заказы доставлены", "заказ"))

    def test_messages_are_indexed_with_the_same_configuration(self) -> None:
        # Конфигурация входит в выражение индекса: разойдись она с запросом —
        # поиск ушёл бы в полный скан. Читаем определение из самой базы, а не
        # из питоновского объекта: в базе лежит то, что реально применится.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE indexname = %s",
                ["conv_message_text_fts"],
            )
            row = cursor.fetchone()
        self.assertIsNotNone(row, "индекс полнотекстового поиска не создан")
        self.assertIn("'russian'", row[0])
        self.assertEqual(
            [i.name for i in Message._meta.indexes if "fts" in i.name],
            ["conv_message_text_fts"],
            "второй индекс под язык не нужен: «russian» уже покрывает латиницу",
        )
