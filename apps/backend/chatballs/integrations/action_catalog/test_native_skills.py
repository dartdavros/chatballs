"""Skill automation retains version conflicts, assignments and safe rendering."""

from uuid import uuid4

from chatballs.ai.agent_card_commands import create
from chatballs.ai.skills_models import Skill
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeSkillTests(CommentTransactionTestBase):
    def test_incomplete_mixed_examples_round_trip_through_save_read_and_update(self):
        _, result = execute_action(self.context, "skills.basis.get", {})
        config = result["configuration"]
        examples = [None, "draft\nline", 42, False, ["mixed", 3, None],
            {"source": "step", "step": "literal-example", "nested": [True, None]}]
        config["templates"][0]["examples"] = examples
        config["templates"][0]["exampleNames"] = []
        run, result = execute_action(self.context, "skills.post", {
            "requestId": str(uuid4()), "configuration": config})
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        identifier = result["skill"]["id"]
        run, result = execute_action(self.context, "skills.detail.get", {"skill_id": identifier})
        self.assertEqual(run.state, "completed")
        self.assertEqual(result["skill"]["templates"][0]["examples"], examples)
        config["templates"][0]["examples"] = list(reversed(examples))
        run, result = execute_action(self.context, "skills.detail.put", {
            "skill_id": identifier, "requestId": str(uuid4()), "expectedRevision": 1, "configuration": config})
        self.assertEqual(run.state, "completed")
        self.assertEqual(result["skill"]["templates"][0]["examples"], list(reversed(examples)))
        with tenant_atomic(self.context):
            self.assertEqual(Skill.objects.get(public_id=identifier).templates[0]["examples"], list(reversed(examples)))

    def test_save_assignment_revision_conflict_and_delete_use_domain_receipts(self):
        config = {"name": "Support", "description": "Support responses", "instruction": "Answer using knowledge.", "templates": []}
        request_id = str(uuid4())
        run, output = execute_action(self.context, "skills.post", {"requestId": request_id, "configuration": config})
        self.assertEqual(run.state, "completed")
        identifier = output["skill"]["id"]
        run_one(self.context, run.public_id)
        run, output = execute_action(self.context, "skills.post", {"requestId": request_id, "configuration": config})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["skill"]["id"], identifier)
        with tenant_atomic(self.context):
            self.assertEqual(Skill.objects.count(), 1)
            agent = create(self.context, {"name": "Support"})["agent"]["id"]
        run, output = execute_action(self.context, "skills.assignment.put", {
            "skill_id": identifier, "agent_id": agent, "expectedRevision": 1})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["skill"]["revision"], 2)
        run, _ = execute_action(self.context, "skills.detail.put", {"skill_id": identifier,
            "requestId": str(uuid4()), "expectedRevision": 1, "configuration": {**config, "name": "Stale"}})
        self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "skills.get", {"agentId": str(agent)})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["connectedAgentCount"], 1)
        self.assertEqual(output["items"][0]["name"], "Support")
        run, output = execute_action(self.context, "skills.deletion.get", {"skill_id": identifier})
        self.assertEqual(run.state, "completed")
        self.assertTrue(output["confirmationRequired"])
        run, _ = execute_action(self.context, "skills.detail.delete", {"skill_id": identifier, "expectedRevision": 2})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertFalse(Skill.objects.filter(public_id=identifier).exists())

    def test_basis_preview_and_foreign_or_employee_access_remain_checked(self):
        run, output = execute_action(self.context, "skills.basis.get", {})
        self.assertEqual(run.state, "completed")
        config = output["configuration"]
        template = config["templates"][0]
        run, output = execute_action(self.context, "skills.preview.post", {"configuration": config,
            "templateId": template["id"], "data": template["examples"][0]})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["presentation"]["isolation"], "sandboxed-iframe")
        self.assertEqual(output["presentation"]["sandbox"], "")
        self.assertTrue(output["text"])
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="skill-employee@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="skills.basis.get", scope="organization")
        run, _ = execute_action(TenantContext.for_membership(member), "skills.basis.get", {})
        self.assertEqual(run.state, "failed")
        foreign_context = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        run, output = execute_action(foreign_context, "skills.post", {"requestId": str(uuid4()), "configuration": config})
        self.assertEqual(run.state, "completed")
        run, _ = execute_action(self.context, "skills.detail.get", {"skill_id": output["skill"]["id"]})
        self.assertEqual(run.state, "failed")
