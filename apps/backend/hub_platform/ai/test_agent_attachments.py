import json

from django.test import TestCase

from hub_platform.ai.agent_knowledge import runtime_portal_articles_for_agent
from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_services import KnowledgeInput, create_knowledge
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import AIAgent, AIAgentStatus, KnowledgeFragment
from hub_platform.ai.retrieval import lexical_search
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.support_portals.content_services import (
    add_revision,
    archive_article,
    create_article,
    publish_revision,
)
from hub_platform.support_portals.content_services import (
    create_category as create_portal_category,
)
from hub_platform.support_portals.models import SupportPortal
from hub_platform.support_portals.portal_services import PortalInput, create_portal
from hub_platform.support_portals.statuses import ArticleStatus
from hub_platform.testing import TenantAPIClient, system_tenant_context


class AgentAttachmentTestCase(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.sales = result.sales_department
        self.support = result.support_department
        self.context = system_tenant_context(self.organization)
        self.category = create_category(context=self.context, name="Library")
        self.support_channel = Channel.objects.create(
            organization=self.organization,
            code="attach-support",
            name="Attach support",
            department=self.support,
        )
        self.sales_channel = Channel.objects.create(
            organization=self.organization,
            code="attach-sales",
            name="Attach sales",
            department=self.sales,
        )
        self.support_agent = AIAgent.objects.create(
            channel=self.support_channel,
            name="Support agent",
            status=AIAgentStatus.ACTIVE,
        )
        self.sales_agent = AIAgent.objects.create(
            channel=self.sales_channel,
            name="Sales agent",
            status=AIAgentStatus.ACTIVE,
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def knowledge(
        self,
        title: str,
        *,
        visibility: str = KnowledgeVisibility.ORGANIZATION,
        department_ids: tuple[int, ...] = (),
    ):
        return create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title=title,
                description="",
                content=f"{title} content",
                is_enabled=True,
                category_id=self.category.id,
                visibility=visibility,
                department_ids=department_ids,
            ),
        )

    def portal(self, slug: str = "attach-help") -> SupportPortal:
        return create_portal(
            context=self.context,
            data=PortalInput(slug=slug, name="Attach Help", default_locale="ru"),
        )

    def article(self, portal: SupportPortal, *, title: str, publish: bool = True):
        category = create_portal_category(
            context=self.context,
            portal=portal,
            data={"name": f"{title} section"},
        )
        article = create_article(
            context=self.context,
            portal=portal,
            data={
                "categoryId": category.id,
                "slug": title.lower().replace(" ", "-"),
                "title": title,
                "summary": f"{title} summary",
                "content": f"{title} article body",
            },
        )
        if publish:
            publish_revision(article=article, revision_id=article.revisions.first().id)
            article.refresh_from_db()
        return article

    def post(self, path: str, payload: dict[str, object]):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )


class AgentKnowledgeLinkApiTests(AgentAttachmentTestCase):
    def test_attach_adds_available_knowledge_and_reports_skipped(self) -> None:
        shared = self.knowledge("Shared")
        sales_only = self.knowledge(
            "Sales only",
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=(self.sales.id,),
        )

        response = self.post(
            "/api/v1/ai/knowledge/bulk/agent/",
            {
                "agentId": self.support_agent.id,
                "knowledgeIds": [shared.id, sales_only.id],
                "action": "attach",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["changedIds"], [shared.id])
        self.assertEqual(payload["skippedIds"], [sales_only.id])
        self.assertEqual(
            set(self.support_agent.knowledge_items.values_list("id", flat=True)),
            {shared.id},
        )

    def test_attach_is_idempotent_for_already_linked_knowledge(self) -> None:
        shared = self.knowledge("Shared")
        self.support_agent.knowledge_items.add(shared)

        response = self.post(
            "/api/v1/ai/knowledge/bulk/agent/",
            {"agentId": self.support_agent.id, "knowledgeIds": [shared.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["changedIds"], [])
        self.assertEqual(self.support_agent.knowledge_items.count(), 1)

    def test_detach_removes_link_without_availability_check(self) -> None:
        scoped = self.knowledge(
            "Support scoped",
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=(self.support.id,),
        )
        self.support_agent.knowledge_items.add(scoped)

        response = self.post(
            "/api/v1/ai/knowledge/bulk/agent/",
            {
                "agentId": self.support_agent.id,
                "knowledgeIds": [scoped.id],
                "action": "detach",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["changedIds"], [scoped.id])
        self.assertFalse(self.support_agent.knowledge_items.exists())

    def test_unknown_knowledge_id_rejects_whole_request(self) -> None:
        shared = self.knowledge("Shared")

        response = self.post(
            "/api/v1/ai/knowledge/bulk/agent/",
            {"agentId": self.support_agent.id, "knowledgeIds": [shared.id, 999999]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.support_agent.knowledge_items.exists())

    def test_unknown_agent_returns_404(self) -> None:
        shared = self.knowledge("Shared")

        response = self.post(
            "/api/v1/ai/knowledge/bulk/agent/",
            {"agentId": 999999, "knowledgeIds": [shared.id]},
        )

        self.assertEqual(response.status_code, 404)


class AgentPortalArticleLinkApiTests(AgentAttachmentTestCase):
    def test_attach_article_to_support_agent(self) -> None:
        article = self.article(self.portal(), title="Refund policy")

        response = self.post(
            "/api/v1/ai/portal-articles/bulk/agent/",
            {"agentId": self.support_agent.id, "articleIds": [article.id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["changedIds"], [article.id])
        self.assertEqual(
            set(self.support_agent.portal_articles.values_list("id", flat=True)),
            {article.id},
        )

    def test_article_is_skipped_for_agent_outside_support_department(self) -> None:
        article = self.article(self.portal(), title="Refund policy")

        response = self.post(
            "/api/v1/ai/portal-articles/bulk/agent/",
            {"agentId": self.sales_agent.id, "articleIds": [article.id]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["changedIds"], [])
        self.assertEqual(payload["skippedIds"], [article.id])
        self.assertFalse(self.sales_agent.portal_articles.exists())

    def test_detach_article_keeps_other_links(self) -> None:
        portal = self.portal()
        first = self.article(portal, title="First")
        second = self.article(portal, title="Second")
        self.support_agent.portal_articles.add(first, second)

        response = self.post(
            "/api/v1/ai/portal-articles/bulk/agent/",
            {
                "agentId": self.support_agent.id,
                "articleIds": [first.id],
                "action": "detach",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.support_agent.portal_articles.values_list("id", flat=True)),
            {second.id},
        )

    def test_agent_payload_lists_attached_articles(self) -> None:
        article = self.article(self.portal(), title="Refund policy")
        self.support_agent.portal_articles.add(article)

        response = self.client.get(f"/api/v1/ai/agents/{self.support_agent.id}/")

        self.assertEqual(response.status_code, 200)
        articles = response.json()["agent"]["portalArticles"]
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["id"], article.id)
        self.assertEqual(articles[0]["title"], "Refund policy")
        self.assertTrue(articles[0]["publicUrl"].endswith("/articles/refund-policy"))


class PortalArticleIndexingTests(AgentAttachmentTestCase):
    def test_publish_indexes_article_and_archive_drops_fragments(self) -> None:
        article = self.article(self.portal(), title="Refund policy")

        self.assertTrue(KnowledgeFragment.objects.filter(portal_article=article).exists())

        archive_article(article)

        self.assertFalse(KnowledgeFragment.objects.filter(portal_article=article).exists())

    def test_draft_article_has_no_fragments(self) -> None:
        article = self.article(self.portal(), title="Draft only", publish=False)

        self.assertEqual(article.status, ArticleStatus.DRAFT)
        self.assertFalse(KnowledgeFragment.objects.filter(portal_article=article).exists())

    def test_republish_replaces_fragments_with_latest_revision(self) -> None:
        article = self.article(self.portal(), title="Refund policy")
        revision = add_revision(
            context=self.context,
            article=article,
            data={
                "title": "Refund policy",
                "summary": "updated summary",
                "content": "Возврат оформляется в течение 14 дней.",
            },
        )
        publish_revision(article=article, revision_id=revision.id)

        contents = list(
            KnowledgeFragment.objects.filter(portal_article=article).values_list(
                "content", flat=True
            )
        )
        self.assertTrue(any("14 дней" in content for content in contents))
        self.assertFalse(any("article body" in content for content in contents))

    def test_retrieval_returns_article_fragments_for_attached_agent(self) -> None:
        article = self.article(self.portal(), title="Refund policy")
        self.support_agent.portal_articles.add(article)

        fragments = lexical_search(self.support_agent, "Refund policy article body")

        self.assertTrue(fragments)
        self.assertEqual(fragments[0].portal_article_id, article.id)
        self.assertEqual(fragments[0].source_title, "Refund policy")

    def test_archived_article_leaves_runtime_selection(self) -> None:
        article = self.article(self.portal(), title="Refund policy")
        self.support_agent.portal_articles.add(article)

        archive_article(article)

        self.assertFalse(runtime_portal_articles_for_agent(self.support_agent).exists())
        self.assertTrue(self.support_agent.portal_articles.filter(id=article.id).exists())
