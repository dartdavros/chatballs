"""Демо-набор «Северный ветер»: покрытие моделей, точное удаление, API."""

from __future__ import annotations

import json
import re
import tempfile
from datetime import timedelta

from django.apps import apps
from django.db import models
from django.test import TestCase, override_settings
from django.utils import timezone

from chatballs.ai.models import AIAgent, AIAgentStatus, Knowledge, KnowledgeAttachment
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.models import (
    Contact,
    Conversation,
    Message,
)
from chatballs.conversations.support_filters import ReportFilters
from chatballs.conversations.support_report import calculate_support_report
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus, DemoRecord
from chatballs.identity.demo_seed import service
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.instance_settings import default_language
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient as APIClient
from chatballs.webchat.models import WebChatWidget

_MEDIA_ROOT = tempfile.mkdtemp(prefix="hub-demo-media-")

OWNER = {
    "organization_name": "Моё ателье",
    "full_name": "Елена Кузнецова",
    "email": "owner@atelie.test",
    "password": "Owner-Setup-2026!",
}

# Модели, которые демо-набор не обязан заполнять: сам реестр, организация
# установщика (уже есть), платформенный контур и очередь событий.
COVERAGE_EXEMPT = {
    ("identity", "organization"),
    ("identity", "demodataset"),
    ("identity", "demorecord"),
    # Настройки хранилища — одна строка на инстанс, не данные организации.
    ("tenancy", "storagesettings"),
    # Настройки установки (адрес, по которому её открывают) — тоже одна
    # строка на инстанс: их пишет мастер первого запуска, а не демо.
    ("identity", "instancesettings"),
    # Состояние обновлений установки — одна строка на инстанс (updates/0001).
    ("updates", "updatestate"),
}
COVERAGE_EXEMPT_APPS = {"platform", "events"}
# Always available in prepared histories. Live sessions, optional local integrations,
# commands and technical state have their own feature tests.
PREPARED_MODELS = {
    "identity.HumanUser", "identity.OrganizationMembership", "identity.EmployeeGroup",
    "channels.Channel", "integrations.Integration", "webchat.WebChatWidget",
    "ai.AIAgent", "ai.Knowledge", "ai.Skill", "ai.AgentSkill", "ai.LlmInvocation",
    "conversations.Contact", "conversations.ConnectionIdentity", "conversations.ContactMerge",
    "conversations.ConversationLabel", "conversations.ReplyTemplate", "conversations.Conversation",
    "conversations.Message", "conversations.ConversationEvent", "conversations.ConversationComment",
    "conversations.ConversationParticipant", "notifications.Notification",
}


def _covered_models() -> list[type[models.Model]]:
    result = []
    for model in apps.get_models():
        label = model._meta.app_label
        if not model.__module__.startswith("chatballs."):
            continue
        if label in COVERAGE_EXEMPT_APPS or (label, model._meta.model_name) in COVERAGE_EXEMPT:
            continue
        result.append(model)
    return result


def _counts() -> dict[str, int]:
    return {m._meta.label: m._base_manager.count() for m in _covered_models()}


def maria_contact_fields(organization) -> tuple[str, str, str]:
    contact = Contact.objects.get(organization=organization, name="Мария Соколова")
    return contact.description, contact.company, contact.city


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DemoDatasetTests(TestCase):
    def setUp(self) -> None:
        result = complete_setup(SetupInput(**OWNER))
        self.organization: Organization = result.organization
        self.owner: HumanUser = result.owner
        self.context = TenantContext.for_resource(
            self.organization, actor_kind=TenantActorKind.SYSTEM, actor_user=self.owner
        )

    def _install(self) -> DemoDataset:
        with tenant_atomic(self.context):
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLING
            )
            return service.install(context=self.context, dataset=dataset)

    def test_install_covers_prepared_demo_models(self) -> None:
        before = _counts()
        dataset = self._install()

        self.assertEqual(dataset.status, DemoDatasetStatus.INSTALLED, dataset.error)
        after = _counts()
        missing = sorted(label for label in PREPARED_MODELS if after[label] <= before[label])
        self.assertEqual(missing, [], f"demo dataset leaves models empty: {missing}")
        self.assertGreater(dataset.records_count, 200)

    def test_dataset_matches_the_design_baseline(self) -> None:
        self._install()
        organization = self.organization

        # Люди: владелец установщика + 6 демо-сотрудников, один заблокирован.
        memberships = OrganizationMembership.objects.filter(organization=organization)
        self.assertEqual(memberships.count(), 7)
        self.assertEqual(memberships.filter(blocked_at__isnull=False).count(), 1)
        anna = HumanUser.objects.get(email="a.kim@severny-veter.test")
        self.assertTrue(anna.check_password("Chatballs-Demo-2026"))
        self.assertTrue(HumanUser.objects.get(email="k.volkov@severny-veter.test").totp_enabled)

        # Агенты: активный с AI, черновик без AI, выключенный канал.
        agents = AIAgent.objects.filter(channel__organization=organization)
        self.assertEqual(agents.filter(status=AIAgentStatus.ACTIVE).count(), 3)
        self.assertEqual(agents.filter(status=AIAgentStatus.DRAFT).count(), 1)
        self.assertEqual(organization.channels.filter(is_active=False).count(), 1)

        # Знания: категории двух уровней, вложения, отключённое знание.
        self.assertGreaterEqual(KnowledgeAttachment.objects.filter(organization=organization).count(), 3)
        self.assertEqual(Knowledge.objects.filter(organization=organization, is_enabled=False).count(), 1)

        # Все диалоги набора относятся к готовым историям «Северного ветра».
        conversations = Conversation.objects.filter(organization=organization)
        self.assertEqual(conversations.count(), 10)
        self.assertFalse(conversations.exclude(external_chat_id__startswith="north-wind:").exists())
        self.assertEqual(conversations.filter(control_mode="HUMAN", lifecycle="OPEN").count(), 10)
        self.assertEqual(conversations.filter(assigned_operator__isnull=False, group__isnull=False).count(), 10)
        self.assertFalse(conversations.filter(priority="NONE").exists())
        self.assertEqual(conversations.filter(labels__isnull=False).distinct().count(), 10)
        self.assertFalse(conversations.filter(created_at__lt=timezone.now() - timedelta(hours=1)).exists())
        self._verify_north_wind_histories(conversations)
        self._verify_weekly_reporting(conversations)
        self.assertEqual(WebChatWidget.objects.filter(organization=organization).count(), 2)
        elena = HumanUser.objects.get(email="e.kuznetsova@severny-veter.test")
        self.assertTrue(elena.avatar, "фото сотрудника из медиа демо")
        self.assertEqual(EmployeeGroup.objects.get(organization=organization, name="Поддержка").color, "#2aa876")
        self.assertEqual(maria_contact_fields(organization), ("Заказ 4471 — горнолыжный костюм. Постоянный клиент с августа, предпочитает Telegram.", "", ""))
        maria = Contact.objects.get(organization=organization, name="Мария Соколова")
        self.assertTrue(maria.avatar_url.startswith("/api/v1/demo-media/avatars/"))

    def _verify_weekly_reporting(self, conversations):
        today = timezone.now().astimezone(MOSCOW).replace(hour=0, minute=0, second=0, microsecond=0)
        events = ConversationEvent.objects.filter(conversation__in=conversations)
        self.assertFalse(events.filter(event_type="CLOSED").exists())
        member = OrganizationMembership.objects.get(organization=self.organization, user=self.owner)
        context = TenantContext.for_membership(member)
        for age in range(7):
            start = today - timedelta(days=age)
            filters = ReportFilters(start, start + timedelta(days=1), str(MOSCOW))
            report = calculate_support_report(context=context, filters=filters)
            counts = report["totals"]["observedCounts"]
            self.assertGreater(counts["accepted"], 0)
            if age:
                self.assertGreater(counts["completed"], 0)
                self.assertEqual(report["details"], [])
            else:
                self.assertEqual(counts["completed"], 0)

    def _verify_north_wind_histories(self, conversations):
        outcomes = {
            "pickup": "Заказ № 2048", "loyalty": "Остаток бонусов: 750",
            "fitting": "Запись № 2043", "exchange": "Замену получил",
            "proposal": "Коммерческое предложение № KP-205", "team": "Замена подошла",
            "delivery": "Пока подожду", "formatted": "Заберу после работы",
            "formatted-external": "Новая дата пока не подтверждена", "exchange-refund": "вижу возврат",
        }
        self.assertEqual(conversations.values("contact_id").distinct().order_by().count(), len(outcomes))
        loyalty = conversations.get(external_chat_id__endswith=":loyalty")
        exchange = conversations.get(external_chat_id__endswith=":exchange")
        self.assertEqual(loyalty.contact.name, exchange.contact.name)
        self.assertTrue(loyalty.messages.filter(text__contains="Заказ № 2042").exists())
        for key, outcome in outcomes.items():
            with self.subTest(scenario=key):
                conversation = conversations.get(external_chat_id__endswith=f":{key}")
                self.assertTrue(conversation.messages.filter(text__contains=outcome).exists())
                self.assertGreaterEqual(conversation.messages.filter(author_type__in=("CONTACT", "OPERATOR", "AI")).count(), 4)
                self.assertTrue(conversation.messages.filter(format_version=1).exists())
                self.assertTrue(conversation.messages.filter(system_event="tool_called", system_params__tool__startswith="MCP").exists())
                self.assertFalse(conversation.messages.filter(text__contains="north-wind.html").exists())
        formatted = conversations.get(external_chat_id__endswith=":formatted")
        self.assertEqual(formatted.messages.filter(format_version=1).count(), 2)
        self.assertEqual(formatted.messages.filter(system_event="tool_called").count(), 4)
        proposal = conversations.get(external_chat_id__endswith=":proposal")
        self.assertTrue(proposal.messages.filter(attachment_name="KP-205.html").exists())
        self.assertTrue(proposal.comments.filter(text__contains="CRM-305").exists())
        for key, count in (("pickup", 4), ("loyalty", 2), ("fitting", 4), ("proposal", 5)):
            dialogue = conversations.get(external_chat_id__endswith=f":{key}")
            cards = dialogue.messages.filter(format_version=1)
            self.assertEqual(cards.count(), count)
            self.assertTrue(all(card.template_snapshot.get("skillId") for card in cards))
        self._verify_reusable_card()

    def _verify_reusable_card(self):
        from chatballs.ai.skill_templates.engine import render_template
        from chatballs.ai.skills_models import Skill

        skill = Skill.objects.get(organization=self.organization, name="Подбор и покупка")
        template = next(item for item in skill.templates if item["name"] == "Карточка товара")
        example = {"title": "Другая модель", "rows": [{"label": "Цена", "value": "35 000 ₽"}]}
        preview = render_template(template, example, language="ru")
        self.assertIn("Другая модель", preview["contentHtml"])
        self.assertIn("Цена: 35 000 ₽", preview["text"])
        self.assertTrue(skill.assignments.filter(agent__channel__organization=self.organization).exists())

    def test_remove_restores_the_exact_state_before_install(self) -> None:
        before = _counts()
        dataset = self._install()
        self.assertEqual(dataset.status, DemoDatasetStatus.INSTALLED, dataset.error)

        with tenant_atomic(self.context):
            service.remove(context=self.context, dataset=DemoDataset.objects.get(pk=dataset.pk))

        after = _counts()
        # Аудит установки и удаления — единственный след администраторских действий.
        after["identity.AuditEvent"] = before["identity.AuditEvent"]
        self.assertEqual(after, before)
        self.assertFalse(DemoDataset.objects.exists())
        self.assertFalse(DemoRecord.objects.exists())
        # Организация и владелец установщика на месте.
        self.assertTrue(Organization.objects.filter(pk=self.organization.pk).exists())
        self.assertTrue(HumanUser.objects.filter(pk=self.owner.pk).exists())


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DemoDatasetApiTests(TestCase):
    """Карточка «Демо-данные»: очередь через outbox, worker выполняет."""

    def setUp(self) -> None:
        complete_setup(SetupInput(**OWNER))
        self.organization = Organization.objects.get()
        self.client = APIClient()
        self.client.login(username=OWNER["email"], password=OWNER["password"])

    def _dispatch_pending(self) -> None:
        for event in OutboxEvent.objects.filter(event_type__startswith="demo.").order_by("id"):
            dispatch(event)
            event.delete()

    def test_install_and_remove_through_api_and_worker(self) -> None:
        self.assertEqual(self.client.get("/api/v1/company/demo/").json()["status"], "ABSENT")

        queued = self.client.post("/api/v1/company/demo/")
        self.assertEqual(queued.status_code, 202)
        self.assertEqual(queued.json()["status"], "INSTALLING")
        # Повторный запрос во время установки отклоняется.
        self.assertEqual(self.client.post("/api/v1/company/demo/").status_code, 409)

        self._dispatch_pending()
        installed = self.client.get("/api/v1/company/demo/").json()
        self.assertEqual(installed["status"], "INSTALLED", installed["error"])
        self.assertGreater(installed["recordsCount"], 200)
        # Витринные учётки: админ и сотрудники из разных групп, с паролем.
        accounts = installed["accounts"]
        self.assertEqual([a["email"] for a in accounts], ["e.kuznetsova@severny-veter.test", "s.petrova@severny-veter.test", "i.saveliev@severny-veter.test"])
        self.assertEqual(accounts[1]["groups"], ["Операторы"])
        self.assertEqual(accounts[2]["groups"], ["Поддержка"])
        self.assertTrue(all(a["password"] == "Chatballs-Demo-2026" for a in accounts))
        self.assertEqual(self.client.post("/api/v1/company/demo/").status_code, 400)

        removing = self.client.delete("/api/v1/company/demo/")
        self.assertEqual(removing.status_code, 202)
        self.assertEqual(removing.json()["status"], "REMOVING")
        self._dispatch_pending()
        self.assertEqual(self.client.get("/api/v1/company/demo/").json()["status"], "ABSENT")
        self.assertFalse(HumanUser.objects.filter(email="a.kim@severny-veter.test").exists())

    def test_employee_cannot_manage_demo(self) -> None:
        self.client.post("/api/v1/company/demo/")
        self._dispatch_pending()
        employee = APIClient()
        employee.login(username="s.petrova@severny-veter.test", password="Chatballs-Demo-2026")
        self.assertEqual(employee.post("/api/v1/company/demo/").status_code, 403)
        self.assertEqual(employee.delete("/api/v1/company/demo/").status_code, 403)



class SetupWizardDemoTests(TestCase):
    def test_setup_wizard_queues_demo_install(self) -> None:
        # Пустой инстанс: мастер с флагом installDemo ставит набор в очередь.
        response = APIClient().post(
            "/api/v1/setup/complete/",
            data=json.dumps(
                {
                    "organizationName": "Ателье Норд",
                    "fullName": "Елена Кузнецова",
                    "email": "e.kuznetsova@severny-veter.test",
                    "password": "Nord-Atelier-2026!",
                    "installDemo": True,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        dataset = DemoDataset.objects.get()
        self.assertEqual(dataset.status, DemoDatasetStatus.INSTALLING)
        self.assertTrue(OutboxEvent.objects.filter(event_type="demo.install_requested").exists())


class EnglishDemoDatasetTests(TestCase):
    """Демо на английской установке: набор ставится английский, целиком.

    Витрина показывает продукт целиком, и русская переписка в английском
    интерфейсе обесценивает её ровно так же, как непереведённая кнопка.
    """

    @override_settings(MEDIA_ROOT=_MEDIA_ROOT)
    def test_english_organization_gets_the_english_dataset(self) -> None:
        result = complete_setup(SetupInput(**OWNER, language="en"))
        organization = result.organization
        context = TenantContext.for_resource(
            organization, actor_kind=TenantActorKind.SYSTEM, actor_user=result.owner
        )
        with tenant_atomic(context):
            dataset = DemoDataset.objects.create(
                organization=organization, status=DemoDatasetStatus.INSTALLING
            )
            dataset = service.install(context=context, dataset=dataset)
        self.assertEqual(dataset.status, DemoDatasetStatus.INSTALLED, dataset.error)

        # Язык установки пришёл из мастера и достался организации по наследству.
        self.assertEqual(default_language(), "en")

        self.assertTrue(
            Contact.objects.filter(organization=organization, name="Maria Sokolova").exists()
        )
        self.assertTrue(
            AIAgent.objects.filter(organization=organization, name="Consultant").exists()
        )
        conversations = Conversation.objects.filter(organization=organization)
        self.assertEqual(conversations.count(), 10)
        self.assertFalse(conversations.exclude(external_chat_id__startswith="north-wind:").exists())
        # Ни одной кириллической буквы во всём, что увидит человек на экране.
        texts = [
            *Message.objects.filter(organization=organization).values_list("text", flat=True),
            *Knowledge.objects.filter(organization=organization).values_list("content", flat=True),
            *Contact.objects.filter(organization=organization).values_list("description", flat=True),
        ]
        cyrillic = [text for text in texts if re.search(r"[А-Яа-яЁё]", text or "")]
        self.assertEqual(cyrillic, [], f"английское демо содержит русский текст: {cyrillic[:3]}")
