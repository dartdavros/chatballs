"""Демо-набор «Ателье Норд»: полное покрытие моделей, точное удаление, API."""

from __future__ import annotations

import json
import tempfile

from django.apps import apps
from django.db import models
from django.test import TestCase, override_settings
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.ai.models import AIAgent, AIAgentStatus, Knowledge, KnowledgeAttachment
from chatballs.conversations.models import (
    Contact,
    Conversation,
    LifecycleState,
    Message,
    MessageKind,
)
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus, DemoRecord
from chatballs.identity.demo_seed import service
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic

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
}
COVERAGE_EXEMPT_APPS = {"platform", "events"}


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


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
def maria_contact_fields(organization) -> tuple[str, str, str]:
    contact = Contact.objects.get(organization=organization, name="Мария Соколова")
    return contact.description, contact.company, contact.city


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

    def test_install_covers_every_model_of_the_system(self) -> None:
        before = _counts()
        dataset = self._install()

        self.assertEqual(dataset.status, DemoDatasetStatus.INSTALLED, dataset.error)
        after = _counts()
        missing = sorted(label for label, count in after.items() if count <= before[label])
        self.assertEqual(missing, [], f"demo dataset leaves models empty: {missing}")
        self.assertGreater(dataset.records_count, 200)

    def test_dataset_matches_the_design_baseline(self) -> None:
        self._install()
        organization = self.organization

        # Люди: владелец установщика + 6 демо-сотрудников, один заблокирован.
        memberships = OrganizationMembership.objects.filter(organization=organization)
        self.assertEqual(memberships.count(), 7)
        self.assertEqual(memberships.filter(blocked_at__isnull=False).count(), 1)
        anna = HumanUser.objects.get(email="a.kim@atelie-nord.ru")
        self.assertTrue(anna.check_password("Chatballs-Demo-2026"))
        self.assertTrue(HumanUser.objects.get(email="k.volkov@atelie-nord.ru").totp_enabled)

        # Агенты: активный с AI, черновик без AI, выключенный канал.
        agents = AIAgent.objects.filter(channel__organization=organization)
        self.assertEqual(agents.filter(status=AIAgentStatus.ACTIVE).count(), 3)
        self.assertEqual(agents.filter(status=AIAgentStatus.DRAFT).count(), 1)
        self.assertEqual(organization.channels.filter(is_active=False).count(), 1)

        # Знания: категории двух уровней, вложения, отключённое знание.
        self.assertGreaterEqual(KnowledgeAttachment.objects.filter(organization=organization).count(), 3)
        self.assertEqual(Knowledge.objects.filter(organization=organization, is_enabled=False).count(), 1)

        # Диалоги во всех состояниях (кадры A–H).
        conversations = Conversation.objects.filter(organization=organization)
        self.assertEqual(conversations.filter(lifecycle=LifecycleState.SPAM).count(), 1)
        self.assertGreaterEqual(conversations.filter(lifecycle=LifecycleState.CLOSED).count(), 3)
        self.assertEqual(conversations.filter(archived_at__isnull=False).count(), 5)
        self.assertEqual(conversations.filter(control_mode="PAUSED", lifecycle="OPEN").count(), 1)
        # Основной список — ровно семь диалогов кадров (архив и спам скрыты).
        self.assertEqual(conversations.filter(archived_at__isnull=True).exclude(lifecycle=LifecycleState.SPAM).count(), 7)
        self.assertTrue(conversations.filter(assigned_operator=anna).exists())
        elena = HumanUser.objects.get(email="e.kuznetsova@atelie-nord.ru")
        self.assertTrue(elena.avatar, "фото сотрудника из медиа демо")
        self.assertEqual(conversations.filter(assigned_operator=elena, lifecycle="OPEN").count(), 2)
        self.assertTrue(conversations.filter(previous_conversation__isnull=False).exists())
        self.assertTrue(conversations.filter(labels__name="срочно").exists())
        self.assertEqual(EmployeeGroup.objects.get(organization=organization, name="Поддержка").color, "#2aa876")
        self.assertEqual(maria_contact_fields(organization), ("Заказ 4471 — комплект штор. Постоянный клиент с августа, предпочитает Telegram.", "", ""))
        # История контакта: у Марии три диалога (кадр F).
        maria = Contact.objects.get(organization=organization, name="Мария Соколова")
        self.assertEqual(conversations.filter(contact=maria).count(), 3)
        self.assertTrue(maria.avatar_url.startswith("/api/v1/demo-media/avatars/"))
        # Веб-гость получил настоящую сессию виджета.
        self.assertTrue(conversations.filter(contact__name__startswith="Гость ·").exists())
        # Гость, который представился (кадр B): имя и фото у анонимной сессии.
        self.assertTrue(conversations.filter(contact__name="Дмитрий Орлов", connection__provider="WEB").exists())
        # Сообщения: контакт-шаринг и системные события есть; голосовые — при наличии файлов.
        messages = Message.objects.filter(conversation__organization=organization)
        self.assertTrue(messages.filter(kind=MessageKind.CONTACT).exists())
        self.assertTrue(messages.filter(author_type="SYSTEM").exists())

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
        self.assertEqual([a["email"] for a in accounts], ["e.kuznetsova@atelie-nord.ru", "s.petrova@atelie-nord.ru", "i.saveliev@atelie-nord.ru"])
        self.assertEqual(accounts[1]["groups"], ["Операторы"])
        self.assertEqual(accounts[2]["groups"], ["Поддержка"])
        self.assertTrue(all(a["password"] == "Chatballs-Demo-2026" for a in accounts))
        self.assertEqual(self.client.post("/api/v1/company/demo/").status_code, 400)

        removing = self.client.delete("/api/v1/company/demo/")
        self.assertEqual(removing.status_code, 202)
        self.assertEqual(removing.json()["status"], "REMOVING")
        self._dispatch_pending()
        self.assertEqual(self.client.get("/api/v1/company/demo/").json()["status"], "ABSENT")
        self.assertFalse(HumanUser.objects.filter(email="a.kim@atelie-nord.ru").exists())

    def test_employee_cannot_manage_demo(self) -> None:
        self.client.post("/api/v1/company/demo/")
        self._dispatch_pending()
        employee = APIClient()
        employee.login(username="s.petrova@atelie-nord.ru", password="Chatballs-Demo-2026")
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
                    "email": "e.kuznetsova@atelie-nord.ru",
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
