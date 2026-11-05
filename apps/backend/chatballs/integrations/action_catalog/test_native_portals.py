"""Portal actions preserve publication, archive, tenancy and native grants."""

from chatballs.ai.models import KnowledgeFragment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.support_portals.feedback_limits import NativeFeedbackThrottle
from chatballs.support_portals.models import PortalArticle, PortalArticleFeedback, SupportPortal
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativePortalTests(CommentTransactionTestBase):
    def execute(self, key, values, *, tenant=None, state="completed"):
        run, output = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return run, output

    def portal(self, *, slug="native-help", tenant=None):
        return self.execute("portals.post", {"slug": slug, "name": "Help"}, tenant=tenant)[1]["portal"]["id"]

    def test_settings_and_status_preserve_audit_filters_and_archive_rules(self):
        identifier = self.portal()
        values = {"portal_id": identifier}
        self.execute("portals.detail.patch", {**values, "name": "Updated help", "themeScheme": "DARK"})
        _, output = self.execute("portals.get", {"q": "Updated", "status": ["DRAFT"]})
        self.assertEqual([row["id"] for row in output["items"]], [identifier])
        self.assertTrue(output["creation"]["canCreate"])
        self.execute("portals.domain.put", {**values, "customDomain": ""})
        self.execute("portals.domain.verify.post", values, state="failed")
        _, output = self.execute("portals.widgets.get", values)
        self.assertEqual(output["items"], [])
        self.execute("portals.public.get", values, state="failed")
        run, _ = self.execute("portals.status.post", {**values, "status": "PUBLISHED"})
        run_one(self.context, run.public_id)
        self.execute("portals.public.get", values)
        self.execute("portals.status.post", {**values, "status": "ARCHIVED"})
        self.execute("portals.detail.patch", {**values, "name": "Forbidden"}, state="failed")
        self.execute("portals.categories.post", {**values, "name": "Forbidden"}, state="failed")
        _, output = self.execute("portals.status.post", {**values, "status": "PUBLISHED"})
        self.assertEqual(output["portal"]["status"], "DRAFT")
        with tenant_atomic(self.context):
            self.assertEqual(AuditEvent.objects.filter(action="support_portal.created").count(), 1)
            self.assertEqual(AuditEvent.objects.filter(action="support_portal.published").count(), 1)
            self.assertEqual(SupportPortal.objects.get(pk=identifier).name, "Updated help")

    def test_content_keeps_revisions_import_feedback_and_search_index(self):
        rates = NativeFeedbackThrottle.THROTTLE_RATES
        self.addCleanup(setattr, NativeFeedbackThrottle, "THROTTLE_RATES", rates)
        NativeFeedbackThrottle.THROTTLE_RATES = {**rates, "help_feedback": "20/hour"}
        identifier = self.portal()
        values = {"portal_id": identifier}
        _, result = self.execute("portals.categories.post", {**values, "name": "Account"})
        category = result["category"]["id"]
        _, result = self.execute("portals.articles.post", {**values, "categoryId": category,
            "slug": "sign-in", "title": "Sign in", "content": "First version"})
        target = {**values, "article_id": result["article"]["id"]}
        self.execute("portals.category.delete", {**values, "category_id": category}, state="failed")
        _, result = self.execute("portals.article.revision.post", {**target, "title": "Sign in", "content": "Published version"})
        revision = result["revision"]["id"]
        _, result = self.execute("portals.article.publish.post", {**target, "revisionId": revision})
        self.assertEqual(len(result["article"]["revisions"]), 2)
        self.assertEqual(result["article"]["publishedRevision"]["content"], "Published version")
        self.execute("portals.status.post", {**values, "status": "PUBLISHED"})
        public = {**values, "article_slug": "sign-in"}
        _, result = self.execute("portals.public.article.get", public)
        self.assertEqual(result["article"]["revision"]["content"], "Published version")
        _, result = self.execute("portals.public.articles.get", {**values, "q": "Published", "direct": True})
        self.assertEqual(result["pagination"]["total"], 1)
        run, _ = self.execute("portals.public.feedback.post", {**public, "helpful": True})
        run_one(self.context, run.public_id)
        throttle = NativeFeedbackThrottle(self.context)
        key = throttle.get_cache_key(None, None)
        self.addCleanup(throttle.cache.delete, key)
        throttle.cache.set(key, [throttle.timer()] * throttle.num_requests, throttle.duration)
        self.execute("portals.public.feedback.post", {**public, "helpful": False}, state="failed")
        with tenant_atomic(self.context):
            self.assertEqual(PortalArticleFeedback.objects.filter(article_id=target["article_id"]).count(), 1)
            self.assertTrue(KnowledgeFragment.objects.filter(portal_article_id=target["article_id"]).exists())
        document = {"categoryPath": ["Account"], "slug": "imported", "title": "Imported", "content": "Imported text"}
        _, result = self.execute("portals.articles.import.post", {**values, "articles": [document]})
        self.assertEqual(result["created"], 1)
        _, result = self.execute("portals.articles.import.post", {**values, "articles": [document]})
        self.assertEqual(result["unchanged"], 1)
        self.execute("portals.article.archive.post", target)
        self.execute("portals.public.article.get", public, state="failed")
        with tenant_atomic(self.context):
            self.assertFalse(KnowledgeFragment.objects.filter(portal_article_id=target["article_id"]).exists())
            self.assertEqual(PortalArticle.objects.get(pk=target["article_id"]).revisions.count(), 2)

    def test_grants_do_not_expand_scope_or_tenant_and_keep_employee_product_permission(self):
        identifier = self.portal()
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="portal-employee@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            grant = ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="portals.categories.post", scope="contact")
        employee = TenantContext.for_membership(member)
        values = {"portal_id": identifier, "name": "Allowed"}
        with self.assertRaises(ExecutionDenied):
            self.execute("portals.categories.post", values, tenant=employee)
        with tenant_atomic(self.context):
            grant.scope = "organization"
            grant.save(update_fields=["scope"])
        self.execute("portals.categories.post", values, tenant=employee)
        foreign_context = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        foreign_id = self.portal(slug="foreign-help", tenant=foreign_context)
        self.execute("portals.categories.post", {"portal_id": foreign_id, "name": "Forbidden"}, tenant=employee, state="failed")
        self.execute("portals.detail.get", {"portal_id": foreign_id}, state="failed")
