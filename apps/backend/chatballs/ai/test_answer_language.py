"""Язык ответов агента: директива системного промпта и её режимы.

Язык ответа задаётся не переводом промпта, а отдельной строкой: промпт читает
модель, и переводить его незачем, — но написан он по-русски и сам по себе
тянет ответ в русский язык. Явное указание это перебивает.
"""

from __future__ import annotations

from django.test import TestCase

from chatballs.ai.models import AIAgent, AnswerLanguage
from chatballs.ai.runtime import (
    ANSWER_IN_CUSTOMER_LANGUAGE,
    answer_language_directive,
)
from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization


class AnswerLanguageDirectiveTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization, code="main", name="Main"
        )

    def _agent(self, answer_language: str) -> AIAgent:
        return AIAgent(
            organization=self.organization,
            channel=self.channel,
            name="Agent",
            answer_language=answer_language,
        )

    def test_default_is_the_language_of_the_client(self) -> None:
        self.assertEqual(AIAgent().answer_language, AnswerLanguage.MIRROR)
        self.assertEqual(
            answer_language_directive(self._agent(AnswerLanguage.MIRROR)),
            ANSWER_IN_CUSTOMER_LANGUAGE,
        )

    def test_fixed_language_names_it_in_the_language_itself(self) -> None:
        # Название языка на нём самом («English», а не «английский»): модели так
        # однозначнее, и перевода названия не требуется.
        directive = answer_language_directive(self._agent("en"))
        self.assertIn("English", directive)
        self.assertNotEqual(directive, ANSWER_IN_CUSTOMER_LANGUAGE)

    def test_organization_mode_follows_the_organization(self) -> None:
        self.organization.language = "en"
        self.organization.save(update_fields=["language"])
        directive = answer_language_directive(self._agent(AnswerLanguage.ORGANIZATION))
        self.assertIn("English", directive)

    def test_unknown_value_falls_back_to_the_client_language(self) -> None:
        # Значение испортили руками или язык убрали из сборки: зеркало клиента
        # безопаснее молчания — ответ всё равно попадёт в язык обращения.
        self.assertEqual(
            answer_language_directive(self._agent("klingon")),
            ANSWER_IN_CUSTOMER_LANGUAGE,
        )
