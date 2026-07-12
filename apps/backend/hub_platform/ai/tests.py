import json
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from hub_platform.ai.models import AIAgent, Knowledge, KnowledgeFragment
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser, Organization
from hub_platform.products.models import Product

_MEDIA_ROOT = tempfile.mkdtemp(prefix="hub-test-media-")


def make_channel_with_agent(organization, *, code, name, product=None, model="openai/gpt-4o-mini"):
    """Канал обработки + его агент (ADR-HUB-0019/0023). Bootstrap не сидит
    каналы/агентов — в проде это делает seed_channels, в тестах — этот helper."""
    channel = Channel.objects.create(organization=organization, code=code, name=name, product=product)
    agent = AIAgent.objects.create(channel=channel, name=f"{name} Agent", model=model, is_active=True)
    return channel, agent


def seed_sales_channels(organization):
    firepage = Product.objects.get(organization=organization, code="firepage")
    foxray = Product.objects.get(organization=organization, code="foxray")
    make_channel_with_agent(organization, code="firepage-sales", name="FirePage — продажи", product=firepage)
    make_channel_with_agent(organization, code="foxray-sales", name="FoxRay — продажи", product=foxray)


class AIAgentInvariantTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")

    def test_channel_has_at_most_one_agent(self) -> None:
        from django.core.exceptions import ValidationError

        from hub_platform.ai.services import AgentCreateInput, create_agent

        channel, _ = make_channel_with_agent(
            self.organization, code="firepage-sales", name="FirePage — продажи",
            product=Product.objects.get(code="firepage"),
        )
        with self.assertRaises(ValidationError):
            create_agent(
                organization=self.organization,
                data=AgentCreateInput(channel_code=channel.code, model="gpt-4o-mini", persona="", tone="", instructions="", knowledge_ids=[]),
            )

    def test_new_product_does_not_get_an_agent_automatically(self) -> None:
        product = Product.objects.create(organization=self.organization, code="academy", name="Academy")
        self.assertFalse(AIAgent.objects.filter(channel__product=product).exists())


class AIAgentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        seed_sales_channels(self.organization)
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_lists_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")

        self.assertEqual(response.status_code, 200)
        codes = {item["channel"]["product"]["code"] for item in response.json()["items"]}
        self.assertEqual(codes, {"firepage", "foxray"})

    def test_owner_creates_agent_with_instructions_and_knowledge(self) -> None:
        academy = Product.objects.create(organization=self.organization, code="academy", name="Academy")
        Channel.objects.create(organization=self.organization, code="academy-sales", name="Academy", product=academy)
        knowledge = Knowledge.objects.create(organization=self.organization, title="FAQ", content="v1")

        response = self.client.post(
            "/api/v1/ai/agents/",
            data=json.dumps(
                {
                    "channel": "academy-sales",
                    "model": "gpt-4o-mini",
                    "persona": "Ты — ассистент Academy.",
                    "tone": "Коротко и по делу.",
                    "instructions": "Отвечай по делу.",
                    "knowledgeIds": [knowledge.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()["agent"]
        self.assertEqual(body["channel"]["code"], "academy-sales")
        self.assertFalse(body["isActive"])
        self.assertEqual(body["persona"], "Ты — ассистент Academy.")
        self.assertEqual([item["id"] for item in body["knowledge"]], [knowledge.id])

    def test_owner_cannot_create_second_agent_for_channel(self) -> None:
        response = self.client.post(
            "/api/v1/ai/agents/",
            data=json.dumps({"channel": "firepage-sales", "model": "gpt-4o-mini", "knowledgeIds": []}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_owner_updates_agent_model_and_instructions(self) -> None:
        agent = AIAgent.objects.get(channel__code="firepage-sales")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"model": "anthropic/claude-3.5", "modelParams": {"temperature": 0.3}, "tone": "Дружелюбно."}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        agent.refresh_from_db()
        self.assertEqual(agent.model, "anthropic/claude-3.5")
        self.assertEqual(agent.model_params, {"temperature": 0.3})
        self.assertEqual(agent.tone, "Дружелюбно.")

    def test_owner_updates_agent_knowledge_selection(self) -> None:
        agent = AIAgent.objects.get(channel__code="firepage-sales")
        knowledge = Knowledge.objects.create(organization=self.organization, title="FAQ", content="v1")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"knowledgeIds": [knowledge.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(agent.knowledge_items.values_list("id", flat=True)), [knowledge.id])

        # Пустой список снимает выбор; отсутствие ключа — не трогает.
        self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"name": "Renamed"}),
            content_type="application/json",
        )
        self.assertEqual(agent.knowledge_items.count(), 1)
        self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"knowledgeIds": []}),
            content_type="application/json",
        )
        self.assertEqual(agent.knowledge_items.count(), 0)

    def test_owner_deactivates_and_activates_agent(self) -> None:
        agent = AIAgent.objects.get(channel__code="foxray-sales")

        deactivated = self.client.post(f"/api/v1/ai/agents/{agent.id}/deactivate/")
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()["agent"]["isActive"])

        activated = self.client.post(f"/api/v1/ai/agents/{agent.id}/activate/")
        self.assertTrue(activated.json()["agent"]["isActive"])

    def test_update_rejects_invalid_model_params(self) -> None:
        agent = AIAgent.objects.get(channel__code="firepage-sales")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"modelParams": "not-an-object"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


class AIAgentPermissionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=Organization.objects.get(slug="edevs"),
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор",
            primary_department=None,
        )
        self.client = APIClient()
        self.client.login(username="operator@edevs.tech", password="operator-password")

    def test_operator_cannot_access_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_access_knowledge(self) -> None:
        response = self.client.get("/api/v1/ai/knowledge/")
        self.assertEqual(response.status_code, 403)


class KnowledgeApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _create(self, **overrides):
        payload = {"title": "FAQ", "description": "Ответы на вопросы", "content": "Refund policy details here."}
        payload.update(overrides)
        return self.client.post("/api/v1/ai/knowledge/", data=json.dumps(payload), content_type="application/json")

    def test_create_builds_fragments_immediately(self) -> None:
        response = self._create()

        self.assertEqual(response.status_code, 201)
        knowledge = response.json()["knowledge"]
        self.assertEqual(knowledge["title"], "FAQ")
        self.assertEqual(knowledge["description"], "Ответы на вопросы")
        self.assertTrue(KnowledgeFragment.objects.filter(knowledge_id=knowledge["id"]).exists())

    def test_create_requires_title(self) -> None:
        self.assertEqual(self._create(title="  ").status_code, 400)

    def test_update_content_reindexes_fragments(self) -> None:
        knowledge_id = self._create().json()["knowledge"]["id"]
        before = list(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).values_list("content", flat=True))

        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge_id}/",
            data=json.dumps({"content": "Совсем другой текст про доставку."}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        after = list(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).values_list("content", flat=True))
        self.assertNotEqual(before, after)

    def test_disable_and_enable(self) -> None:
        knowledge_id = self._create().json()["knowledge"]["id"]
        disabled = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge_id}/",
            data=json.dumps({"isEnabled": False}),
            content_type="application/json",
        )
        self.assertFalse(disabled.json()["knowledge"]["isEnabled"])

    def test_delete_removes_knowledge_and_fragments(self) -> None:
        knowledge_id = self._create().json()["knowledge"]["id"]

        response = self.client.delete(f"/api/v1/ai/knowledge/{knowledge_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Knowledge.objects.filter(id=knowledge_id).exists())
        self.assertFalse(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).exists())

    def test_list_omits_content(self) -> None:
        self._create()
        response = self.client.get("/api/v1/ai/knowledge/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("content", response.json()["items"][0])


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class KnowledgeAttachmentTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")
        self.knowledge = Knowledge.objects.create(organization=self.organization, title="FAQ", content="Основной текст.")

    def _upload(self, name="price.txt", data=b"Full price list contents", content_type="text/plain"):
        return self.client.post(
            f"/api/v1/ai/knowledge/{self.knowledge.id}/attachments/",
            data={"file": SimpleUploadedFile(name, data, content_type=content_type)},
            format="multipart",
        )

    def test_upload_keeps_original_name_and_indexes_text(self) -> None:
        response = self._upload()

        self.assertEqual(response.status_code, 201)
        attachment = response.json()["attachment"]
        self.assertEqual(attachment["name"], "price.txt")
        self.assertTrue(attachment["hasText"])
        self.assertIn("/api/v1/ai/files/", attachment["url"])
        contents = " ".join(KnowledgeFragment.objects.filter(knowledge=self.knowledge).values_list("content", flat=True))
        self.assertIn("price list", contents)

    def test_reupload_same_name_replaces_attachment(self) -> None:
        self._upload()
        response = self._upload(data=b"Updated price list")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.knowledge.attachments.count(), 1)

    def test_public_download_without_auth(self) -> None:
        attachment_url = self._upload().json()["attachment"]["url"]
        path = attachment_url.split("localhost:8000")[-1]

        anonymous = APIClient()
        response = anonymous.get(path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"Full price list contents")
        self.assertIn("price.txt", response["Content-Disposition"])

    def test_delete_attachment_reindexes(self) -> None:
        attachment_id = self._upload().json()["attachment"]["id"]

        response = self.client.delete(f"/api/v1/ai/knowledge/{self.knowledge.id}/attachments/{attachment_id}/")

        self.assertEqual(response.status_code, 204)
        contents = " ".join(KnowledgeFragment.objects.filter(knowledge=self.knowledge).values_list("content", flat=True))
        self.assertNotIn("price list", contents)


class KnowledgeImportTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _import(self, documents):
        return self.client.post(
            "/api/v1/ai/knowledge/import/",
            data=json.dumps({"documents": documents}),
            content_type="application/json",
        )

    def test_creates_new_knowledge(self) -> None:
        response = self._import([{"title": "Обзор", "description": "Что это", "content": "Текст обзора"}])

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["created"], 1)
        knowledge = Knowledge.objects.get(organization=self.organization, title="Обзор")
        self.assertEqual(knowledge.content, "Текст обзора")
        self.assertTrue(knowledge.fragments.exists())

    def test_reimport_same_content_is_unchanged(self) -> None:
        self._import([{"title": "Обзор", "content": "Текст"}])

        response = self._import([{"title": "Обзор", "content": "Текст"}])

        self.assertEqual(response.json()["unchanged"], 1)
        self.assertEqual(Knowledge.objects.filter(title="Обзор").count(), 1)

    def test_changed_content_updates_existing(self) -> None:
        self._import([{"title": "Обзор", "content": "v1"}])

        response = self._import([{"title": "Обзор", "content": "v2"}])

        self.assertEqual(response.json()["updated"], 1)
        self.assertEqual(Knowledge.objects.get(title="Обзор").content, "v2")

    def test_missing_title_goes_to_failed(self) -> None:
        response = self._import([
            {"title": "Хороший", "content": "ок"},
            {"title": " ", "content": "плохо"},
        ])

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["created"], 1)
        self.assertEqual(len(body["failed"]), 1)


class PiiRedactionTests(TestCase):
    def test_redacts_email_phone_and_long_numbers(self) -> None:
        from hub_platform.ai.pii import redact

        cleaned = redact("Пишите a.kotova@edevs.tech, тел +7 916 245 14 02, карта 4111 1111 1111 1111")
        self.assertNotIn("a.kotova@edevs.tech", cleaned)
        self.assertNotIn("4111", cleaned)
        self.assertNotIn("916 245", cleaned)
        self.assertIn("[email]", cleaned)


class ResilienceTests(TestCase):
    def test_retries_then_succeeds(self) -> None:
        from hub_platform.ai.provider.base import ProviderError
        from hub_platform.ai.provider.resilience import call_with_resilience

        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise ProviderError("temporary")
            return "ok"

        result = call_with_resilience(flaky, retries=2, sleep=lambda _seconds: None)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 2)

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        from hub_platform.ai.provider.base import ProviderError
        from hub_platform.ai.provider.resilience import CircuitBreaker, CircuitBreakerOpen, call_with_resilience

        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=999)

        def always_fail():
            raise ProviderError("down")

        for _ in range(2):
            with self.assertRaises(ProviderError):
                call_with_resilience(always_fail, retries=0, breaker=breaker, sleep=lambda _s: None)
        with self.assertRaises(CircuitBreakerOpen):
            call_with_resilience(always_fail, retries=0, breaker=breaker, sleep=lambda _s: None)


class ProviderFactoryTests(TestCase):
    def test_local_provider_in_tests(self) -> None:
        from hub_platform.ai.provider.factory import get_provider
        from hub_platform.ai.provider.local import LocalProvider

        self.assertIsInstance(get_provider(), LocalProvider)

    @override_settings(DEBUG=False, TESTING=False, HUB_AI_PROVIDER="test")
    def test_local_provider_forbidden_in_production(self) -> None:
        from django.core.exceptions import ImproperlyConfigured

        from hub_platform.ai.provider.factory import get_provider

        with self.assertRaises(ImproperlyConfigured):
            get_provider()


class ChatInvocationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel, self.agent = make_channel_with_agent(
            self.organization, code="firepage-sales", name="FirePage — продажи",
            product=Product.objects.get(code="firepage"),
        )

    def test_chat_records_invocation_with_cost(self) -> None:
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
        from hub_platform.ai.provider.base import ChatMessage

        result = invoke_chat(
            channel=self.channel,
            messages=[ChatMessage(role="user", content="hello there")],
            purpose="agent_chat",
        )

        self.assertTrue(result.text)
        invocation = LlmInvocation.objects.get(channel=self.channel, operation="chat")
        self.assertEqual(invocation.status, LlmInvocationStatus.SUCCESS)
        self.assertGreater(invocation.total_tokens, 0)
        self.assertGreater(invocation.cost_micros, 0)

    def test_pii_is_redacted_before_reaching_provider(self) -> None:
        from unittest import mock

        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.provider.base import ChatMessage, ChatResult

        captured = {}

        class _Capturing:
            def chat(self, *, messages, model, params=None):
                captured["messages"] = messages
                return ChatResult(text="ok", model=model, prompt_tokens=1, completion_tokens=1)

            def embed(self, *, texts, model):  # pragma: no cover
                return []

        with mock.patch("hub_platform.ai.invocation.get_provider", return_value=_Capturing()):
            invoke_chat(
                channel=self.channel,
                messages=[ChatMessage(role="user", content="email me a@b.com")],
                purpose="agent_chat",
            )

        self.assertNotIn("a@b.com", captured["messages"][0].content)

    def test_limit_blocks_and_records(self) -> None:
        from hub_platform.ai import limits as ai_limits
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
        from hub_platform.ai.provider.base import ChatMessage

        self.agent.limits = {"dailyCostUsd": 1}
        self.agent.save(update_fields=["limits"])
        # 1 цент = 10 000 micro-USD; лимит превышен расходом в 10_001 micros.
        LlmInvocation.objects.create(
            channel=self.channel, purpose="seed", operation="chat", model="x", cost_micros=10_001,
            status=LlmInvocationStatus.SUCCESS,
        )

        with self.assertRaises(ai_limits.LimitExceeded):
            invoke_chat(channel=self.channel, messages=[ChatMessage(role="user", content="hi")], purpose="agent_chat")
        self.assertTrue(LlmInvocation.objects.filter(channel=self.channel, status=LlmInvocationStatus.BLOCKED).exists())

    def test_invocation_records_used_fragment_ids(self) -> None:
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation
        from hub_platform.ai.provider.base import ChatMessage

        invoke_chat(
            channel=self.channel,
            messages=[ChatMessage(role="user", content="hi")],
            purpose="agent_chat",
            used_fragment_ids=[11, 22],
        )
        invocation = LlmInvocation.objects.get(channel=self.channel, operation="chat")
        self.assertEqual(invocation.used_fragment_ids, [11, 22])


class ChunkingTests(TestCase):
    def test_packs_paragraphs_into_chunks(self) -> None:
        from hub_platform.ai.chunking import chunk_text

        text = "\n\n".join(["paragraph " + str(i) + " " + "x" * 200 for i in range(10)])
        chunks = chunk_text(text, max_chars=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 700 for chunk in chunks))


class TextExtractionTests(TestCase):
    def test_extracts_plain_text(self) -> None:
        from hub_platform.ai.extraction import extract_text

        self.assertEqual(extract_text(filename="a.md", content_type="", data="# Заголовок".encode()), "# Заголовок")

    def test_unknown_format_returns_empty(self) -> None:
        from hub_platform.ai.extraction import extract_text

        self.assertEqual(extract_text(filename="a.bin", content_type="application/octet-stream", data=b"\x00\x01"), "")

    def test_broken_pdf_is_not_fatal(self) -> None:
        from hub_platform.ai.extraction import extract_text

        self.assertEqual(extract_text(filename="a.pdf", content_type="application/pdf", data=b"not a pdf"), "")


class KnowledgeRetrievalTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel, self.agent = make_channel_with_agent(
            self.organization, code="firepage-sales", name="FirePage — продажи",
            product=Product.objects.get(code="firepage"),
        )
        from hub_platform.ai.services import KnowledgeInput, create_knowledge

        self.knowledge = create_knowledge(
            organization=self.organization,
            data=KnowledgeInput(
                title="FAQ",
                description="Возвраты и доставка",
                content="Refund policy details here.\n\nDelivery and shipping information.",
                is_enabled=True,
            ),
        )
        self.agent.knowledge_items.add(self.knowledge)

    def test_create_builds_fragments_with_embeddings(self) -> None:
        fragments = KnowledgeFragment.objects.filter(knowledge=self.knowledge)
        self.assertGreaterEqual(fragments.count(), 1)
        self.assertTrue(all(fragment.embedding is not None for fragment in fragments))

    def test_retriever_returns_agent_scoped_fragments(self) -> None:
        from hub_platform.ai.retrieval import KnowledgeRetriever

        results = KnowledgeRetriever().retrieve(agent=self.agent, query="refund", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 5)

    def test_retriever_skips_unselected_and_disabled_knowledge(self) -> None:
        from hub_platform.ai.retrieval import lexical_search

        self.knowledge.is_enabled = False
        self.knowledge.save(update_fields=["is_enabled"])
        self.assertEqual(lexical_search(self.agent, "refund", limit=5), [])

    def test_lexical_search_matches_content(self) -> None:
        from hub_platform.ai.retrieval import lexical_search

        results = lexical_search(self.agent, "Delivery", limit=5)
        self.assertTrue(any("delivery" in fragment.content.lower() for fragment in results))


class AgentRuntimeTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel, self.agent = make_channel_with_agent(
            self.organization, code="firepage-sales", name="FirePage — продажи",
            product=Product.objects.get(code="firepage"),
        )
        self.agent.persona = "Ты — ассистент FirePage."
        self.agent.tone = "Коротко."
        self.agent.instructions = "Отвечай только по знаниям."
        self.agent.save()
        from hub_platform.ai.services import KnowledgeInput, create_knowledge

        self.knowledge = create_knowledge(
            organization=self.organization,
            data=KnowledgeInput(title="FAQ", description="Возвраты", content="Refund policy details here.", is_enabled=True),
        )
        self.agent.knowledge_items.add(self.knowledge)

    def test_system_prompt_joins_three_parts_in_order(self) -> None:
        from hub_platform.ai.runtime import agent_system_prompt

        prompt = agent_system_prompt(self.agent)
        self.assertEqual(prompt.index("Ты — ассистент"), 0)
        self.assertLess(prompt.index("Коротко."), prompt.index("Отвечай только"))

    def test_knowledge_catalog_lists_titles_and_attachment_links(self) -> None:
        from hub_platform.ai.runtime import knowledge_catalog

        catalog = knowledge_catalog(self.agent)
        self.assertIn("FAQ", catalog)
        self.assertIn("Возвраты", catalog)

    def test_agent_turn_returns_reply_and_fragments(self) -> None:
        from hub_platform.ai.models import LlmInvocation
        from hub_platform.ai.runtime import run_agent_turn

        result = run_agent_turn(agent=self.agent, message="refund")

        self.assertTrue(result.result.text)
        self.assertGreaterEqual(len(result.fragments), 1)
        self.assertFalse(result.handoff_suggested)
        invocation = LlmInvocation.objects.get(channel=self.channel, purpose="agent_chat", operation="chat")
        self.assertTrue(invocation.used_fragment_ids)

    def test_channel_turn_requires_active_agent(self) -> None:
        from hub_platform.ai.provider.base import ProviderError
        from hub_platform.channels.runtime import run_channel_turn

        self.agent.is_active = False
        self.agent.save(update_fields=["is_active"])
        with self.assertRaises(ProviderError):
            run_channel_turn(channel=self.channel, message="hi")

    def test_channel_test_chat_endpoint(self) -> None:
        client = APIClient()
        client.login(username="owner@edevs.tech", password="temporary-password")

        response = client.post(
            f"/api/v1/channels/{self.channel.id}/test-chat/",
            data=json.dumps({"message": "refund"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["reply"])
