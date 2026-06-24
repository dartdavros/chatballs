import json

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from hub_platform.ai.models import AIAgent
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser, Organization
from hub_platform.products.models import Product


class AIAgentInvariantTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")

    def test_each_product_has_exactly_one_agent(self) -> None:
        product_codes = set(Product.objects.values_list("code", flat=True))
        agent_codes = set(AIAgent.objects.values_list("product__code", flat=True))
        self.assertEqual(agent_codes, product_codes)
        self.assertEqual(AIAgent.objects.count(), Product.objects.count())

    def test_new_product_gets_an_agent(self) -> None:
        org = Organization.objects.get(slug="edevs")
        product = Product.objects.create(organization=org, code="academy", name="Academy")
        self.assertTrue(AIAgent.objects.filter(product=product).exists())


class AIAgentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_lists_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")

        self.assertEqual(response.status_code, 200)
        codes = {item["product"]["code"] for item in response.json()["items"]}
        self.assertEqual(codes, {"firepage", "foxray"})

    def test_owner_updates_agent_model(self) -> None:
        agent = AIAgent.objects.get(product__code="firepage")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"model": "anthropic/claude-3.5", "modelParams": {"temperature": 0.3}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        agent.refresh_from_db()
        self.assertEqual(agent.model, "anthropic/claude-3.5")
        self.assertEqual(agent.model_params, {"temperature": 0.3})

    def test_owner_deactivates_and_activates_agent(self) -> None:
        agent = AIAgent.objects.get(product__code="foxray")

        deactivated = self.client.post(f"/api/v1/ai/agents/{agent.id}/deactivate/")
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()["agent"]["isActive"])

        activated = self.client.post(f"/api/v1/ai/agents/{agent.id}/activate/")
        self.assertTrue(activated.json()["agent"]["isActive"])

    def test_update_rejects_invalid_model_params(self) -> None:
        agent = AIAgent.objects.get(product__code="firepage")

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
            role=EmployeeRole.OPERATOR,
            department=None,
        )
        self.client = APIClient()
        self.client.login(username="operator@edevs.tech", password="operator-password")

    def test_operator_cannot_access_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_access_knowledge(self) -> None:
        response = self.client.get("/api/v1/ai/knowledge/")
        self.assertEqual(response.status_code, 403)


class KnowledgeDocumentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _create(self, **overrides):
        payload = {"product": "firepage", "code": "faq", "title": "FAQ", "category": "FAQ", "content": "v1"}
        payload.update(overrides)
        return self.client.post("/api/v1/ai/knowledge/", data=json.dumps(payload), content_type="application/json")

    def test_create_makes_first_draft_version(self) -> None:
        response = self._create()

        self.assertEqual(response.status_code, 201)
        document = response.json()["document"]
        self.assertEqual(document["category"], "FAQ")
        self.assertEqual(document["inclusionMode"], "RETRIEVAL")
        self.assertEqual(len(document["versions"]), 1)
        self.assertEqual(document["versions"][0]["status"], "DRAFT")
        self.assertEqual(document["versions"][0]["content"], "v1")

    def test_add_version_then_publish_archives_previous(self) -> None:
        document_id = self._create().json()["document"]["id"]
        self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/versions/",
            data=json.dumps({"content": "v2"}),
            content_type="application/json",
        )
        self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/1/publish/")
        response = self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/2/publish/")

        self.assertEqual(response.status_code, 200)
        versions = {v["version"]: v["status"] for v in response.json()["document"]["versions"]}
        self.assertEqual(versions[2], "PUBLISHED")
        self.assertEqual(versions[1], "ARCHIVED")

    def test_rollback_creates_new_draft_from_old_content(self) -> None:
        document_id = self._create().json()["document"]["id"]
        self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/versions/",
            data=json.dumps({"content": "v2"}),
            content_type="application/json",
        )
        response = self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/rollback/",
            data=json.dumps({"version": 1}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        versions = response.json()["document"]["versions"]
        latest = max(versions, key=lambda v: v["version"])
        self.assertEqual(latest["version"], 3)
        self.assertEqual(latest["status"], "DRAFT")
        self.assertEqual(latest["content"], "v1")

    def test_create_rejects_unknown_category(self) -> None:
        self.assertEqual(self._create(category="NOPE").status_code, 400)

    def test_disable_and_enable(self) -> None:
        document_id = self._create().json()["document"]["id"]
        disabled = self.client.post(f"/api/v1/ai/knowledge/{document_id}/disable/")
        self.assertFalse(disabled.json()["document"]["isEnabled"])
        enabled = self.client.post(f"/api/v1/ai/knowledge/{document_id}/enable/")
        self.assertTrue(enabled.json()["document"]["isEnabled"])

    def test_create_for_foreign_product_is_rejected(self) -> None:
        Organization.objects.create(name="Other", slug="other")
        # product code resolved within the owner's organization only
        response = self._create(product="missing")
        self.assertEqual(response.status_code, 400)


class PromptDocumentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_create_prompt_without_inclusion_mode(self) -> None:
        response = self.client.post(
            "/api/v1/ai/prompts/",
            data=json.dumps({"product": "foxray", "code": "system", "title": "System", "category": "SYSTEM", "content": "be helpful"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        document = response.json()["document"]
        self.assertEqual(document["category"], "SYSTEM")
        self.assertNotIn("inclusionMode", document)
        self.assertEqual(document["versions"][0]["content"], "be helpful")

    def test_prompt_rejects_knowledge_category(self) -> None:
        response = self.client.post(
            "/api/v1/ai/prompts/",
            data=json.dumps({"product": "foxray", "code": "x", "title": "X", "category": "FAQ", "content": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class ProductAIReleaseApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")
        document_id = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps({"product": "firepage", "code": "faq", "title": "FAQ", "category": "FAQ", "content": "v1"}),
            content_type="application/json",
        ).json()["document"]["id"]
        self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/1/publish/")

    def _create_release(self):
        return self.client.post(
            "/api/v1/ai/releases/",
            data=json.dumps({"product": "firepage"}),
            content_type="application/json",
        )

    def test_draft_release_snapshots_published_knowledge_and_agent_config(self) -> None:
        response = self._create_release()

        self.assertEqual(response.status_code, 201)
        release = response.json()["release"]
        self.assertEqual(release["status"], "DRAFT")
        self.assertEqual(release["version"], 1)
        self.assertEqual(release["model"], "openai/gpt-4o-mini")
        self.assertIn({"document": "faq", "version": 1}, release["knowledgeVersions"])

    def test_publishing_a_release_archives_the_previous_active_one(self) -> None:
        first = self._create_release().json()["release"]
        self.client.post(f"/api/v1/ai/releases/{first['id']}/publish/")
        second = self._create_release().json()["release"]
        self.client.post(f"/api/v1/ai/releases/{second['id']}/publish/")

        first_detail = self.client.get(f"/api/v1/ai/releases/{first['id']}/").json()["release"]
        second_detail = self.client.get(f"/api/v1/ai/releases/{second['id']}/").json()["release"]
        self.assertEqual(first_detail["status"], "ARCHIVED")
        self.assertEqual(second_detail["status"], "PUBLISHED")

    def test_rollback_creates_new_draft_from_snapshot(self) -> None:
        first = self._create_release().json()["release"]
        self.client.post(f"/api/v1/ai/releases/{first['id']}/publish/")

        response = self.client.post(f"/api/v1/ai/releases/{first['id']}/rollback/")

        self.assertEqual(response.status_code, 201)
        rolled = response.json()["release"]
        self.assertEqual(rolled["status"], "DRAFT")
        self.assertGreater(rolled["version"], first["version"])
        self.assertEqual(rolled["knowledgeVersions"], first["knowledgeVersions"])

    def test_release_snapshot_is_immutable(self) -> None:
        from django.core.exceptions import ValidationError

        from hub_platform.ai.models import ProductAIRelease

        release_id = self._create_release().json()["release"]["id"]
        release = ProductAIRelease.objects.get(id=release_id)
        release.model = "anthropic/claude-3.5"
        with self.assertRaises(ValidationError):
            release.save()


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
        self.product = Product.objects.get(code="firepage")

    def test_chat_records_invocation_with_cost(self) -> None:
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
        from hub_platform.ai.provider.base import ChatMessage

        result = invoke_chat(
            product=self.product,
            messages=[ChatMessage(role="user", content="hello there")],
            purpose="test_chat",
        )

        self.assertTrue(result.text)
        invocation = LlmInvocation.objects.get(product=self.product, operation="chat")
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
                product=self.product,
                messages=[ChatMessage(role="user", content="email me a@b.com")],
                purpose="test_chat",
            )

        self.assertNotIn("a@b.com", captured["messages"][0].content)

    def test_limit_blocks_and_records(self) -> None:
        from hub_platform.ai import limits as ai_limits
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus
        from hub_platform.ai.provider.base import ChatMessage

        agent = self.product.ai_agent
        agent.limits = {"dailyCostMicros": 1}
        agent.save(update_fields=["limits"])
        LlmInvocation.objects.create(
            product=self.product, purpose="seed", operation="chat", model="x", cost_micros=10,
            status=LlmInvocationStatus.SUCCESS,
        )

        with self.assertRaises(ai_limits.LimitExceeded):
            invoke_chat(product=self.product, messages=[ChatMessage(role="user", content="hi")], purpose="test_chat")
        self.assertTrue(LlmInvocation.objects.filter(product=self.product, status=LlmInvocationStatus.BLOCKED).exists())

    def test_invocation_records_used_fragment_ids(self) -> None:
        from hub_platform.ai.invocation import invoke_chat
        from hub_platform.ai.models import LlmInvocation
        from hub_platform.ai.provider.base import ChatMessage

        invoke_chat(
            product=self.product,
            messages=[ChatMessage(role="user", content="hi")],
            purpose="test_chat",
            used_fragment_ids=[11, 22],
        )
        invocation = LlmInvocation.objects.get(product=self.product, operation="chat")
        self.assertEqual(invocation.used_fragment_ids, [11, 22])


class ChunkingTests(TestCase):
    def test_packs_paragraphs_into_chunks(self) -> None:
        from hub_platform.ai.chunking import chunk_text

        text = "\n\n".join(["paragraph " + str(i) + " " + "x" * 200 for i in range(10)])
        chunks = chunk_text(text, max_chars=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 700 for chunk in chunks))


class KnowledgeRetrievalTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")
        document_id = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps(
                {
                    "product": "firepage",
                    "code": "faq",
                    "title": "FAQ",
                    "category": "FAQ",
                    "content": "Refund policy details here.\n\nDelivery and shipping information.",
                }
            ),
            content_type="application/json",
        ).json()["document"]["id"]
        self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/1/publish/")

        from hub_platform.ai import releases

        self.product = Product.objects.get(code="firepage")
        owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.release = releases.create_draft_release(product=self.product, author=owner)

    def test_publish_builds_fragments_with_embeddings(self) -> None:
        from hub_platform.ai.models import KnowledgeFragment

        fragments = KnowledgeFragment.objects.filter(version__document__code="faq")
        self.assertGreaterEqual(fragments.count(), 1)
        self.assertTrue(all(fragment.embedding is not None for fragment in fragments))

    def test_retriever_returns_release_scoped_fragments(self) -> None:
        from hub_platform.ai.retrieval import KnowledgeRetriever

        results = KnowledgeRetriever().retrieve(release=self.release, query="refund", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 5)

    def test_lexical_search_matches_content(self) -> None:
        from hub_platform.ai.retrieval import lexical_search

        results = lexical_search(self.release, "Delivery", limit=5)
        self.assertTrue(any("delivery" in fragment.content.lower() for fragment in results))


class TestChatRuntimeTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")
        document_id = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps(
                {"product": "firepage", "code": "faq", "title": "FAQ", "category": "FAQ", "content": "Refund policy details here."}
            ),
            content_type="application/json",
        ).json()["document"]["id"]
        self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/1/publish/")

        from hub_platform.ai import releases

        owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.release = releases.create_draft_release(product=Product.objects.get(code="firepage"), author=owner)

    def test_test_chat_returns_reply_and_records_used_knowledge(self) -> None:
        from hub_platform.ai.models import LlmInvocation

        response = self.client.post(
            f"/api/v1/ai/releases/{self.release.id}/test-chat/",
            data=json.dumps({"message": "refund"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["reply"])
        self.assertGreater(body["totalTokens"], 0)
        self.assertFalse(body["handoffSuggested"])
        self.assertGreaterEqual(len(body["usedKnowledge"]), 1)
        invocation = LlmInvocation.objects.get(release=self.release, purpose="test_chat", operation="chat")
        self.assertTrue(invocation.used_fragment_ids)

    def test_test_chat_suggests_handoff_without_knowledge(self) -> None:
        from hub_platform.ai import releases

        owner = HumanUser.objects.get(email="owner@edevs.tech")
        empty_release = releases.create_draft_release(product=Product.objects.get(code="foxray"), author=owner)

        response = self.client.post(
            f"/api/v1/ai/releases/{empty_release.id}/test-chat/",
            data=json.dumps({"message": "anything"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["handoffSuggested"])
        self.assertEqual(response.json()["usedKnowledge"], [])

    def test_test_chat_requires_message(self) -> None:
        response = self.client.post(
            f"/api/v1/ai/releases/{self.release.id}/test-chat/",
            data=json.dumps({"message": "  "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
