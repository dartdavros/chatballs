from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class KnowledgeCategoryMigrationTests(TransactionTestCase):
    migrate_from = [
        ("ai", "0009_knowledge_hierarchy_and_visibility"),
        ("channels", "0004_remove_channel_ai_fields"),
    ]
    migrate_to = [
        ("ai", "0011_require_knowledge_category"),
        ("channels", "0004_remove_channel_ai_fields"),
    ]

    def setUp(self) -> None:
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        Organization = old_apps.get_model("identity", "Organization")
        Department = old_apps.get_model("identity", "Department")
        Channel = old_apps.get_model("channels", "Channel")
        Knowledge = old_apps.get_model("ai", "Knowledge")
        KnowledgeAttachment = old_apps.get_model("ai", "KnowledgeAttachment")
        KnowledgeCategory = old_apps.get_model("ai", "KnowledgeCategory")
        KnowledgeDepartment = old_apps.get_model("ai", "KnowledgeDepartment")
        KnowledgeFragment = old_apps.get_model("ai", "KnowledgeFragment")
        AIAgent = old_apps.get_model("ai", "AIAgent")

        organization = Organization.objects.create(name="Legacy", slug="legacy-knowledge")
        empty_organization = Organization.objects.create(
            name="Empty",
            slug="empty-knowledge",
        )
        department = Department.objects.create(
            organization=organization,
            code="support",
            name="Support",
        )
        channel = Channel.objects.create(
            organization=organization,
            department=department,
            code="support-web",
            name="Support Web",
        )
        legacy_knowledge = Knowledge.objects.create(
            organization=organization,
            title="Legacy FAQ",
            content="Original content",
        )
        Knowledge.objects.filter(pk=legacy_knowledge.pk).update(visibility="DEPARTMENTS")
        attachment = KnowledgeAttachment.objects.create(
            organization=organization,
            knowledge=legacy_knowledge,
            file="organizations/legacy/knowledge/faq.txt",
            original_name="faq.txt",
            extracted_text="Attachment content",
            size=18,
        )
        fragment = KnowledgeFragment.objects.create(
            organization=organization,
            knowledge=legacy_knowledge,
            chunk_index=0,
            content="Indexed fragment",
        )
        agent = AIAgent.objects.create(
            organization=organization,
            channel=channel,
            name="Support Agent",
        )
        agent.knowledge_items.add(legacy_knowledge)

        custom_category = KnowledgeCategory.objects.create(
            organization=organization,
            name="Already classified",
        )
        classified_knowledge = Knowledge.objects.create(
            organization=organization,
            category=custom_category,
            title="Classified",
            visibility="DEPARTMENTS",
        )
        KnowledgeDepartment.objects.create(
            organization=organization,
            knowledge=classified_knowledge,
            department=department,
        )

        self.organization_id = organization.pk
        self.empty_organization_id = empty_organization.pk
        self.legacy_knowledge_id = legacy_knowledge.pk
        self.classified_knowledge_id = classified_knowledge.pk
        self.custom_category_id = custom_category.pk
        self.attachment_id = attachment.pk
        self.fragment_id = fragment.pk
        self.agent_id = agent.pk

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_forward_and_reverse_preserve_runtime_data(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        new_apps = executor.loader.project_state(self.migrate_to).apps

        Knowledge = new_apps.get_model("ai", "Knowledge")
        KnowledgeAttachment = new_apps.get_model("ai", "KnowledgeAttachment")
        KnowledgeCategory = new_apps.get_model("ai", "KnowledgeCategory")
        KnowledgeDepartment = new_apps.get_model("ai", "KnowledgeDepartment")
        KnowledgeFragment = new_apps.get_model("ai", "KnowledgeFragment")
        AIAgent = new_apps.get_model("ai", "AIAgent")

        legacy = Knowledge.objects.get(pk=self.legacy_knowledge_id)
        self.assertEqual(legacy.category.name, "Без категории")
        self.assertTrue(legacy.category.is_system)
        self.assertEqual(legacy.visibility, "ORGANIZATION")
        self.assertFalse(Knowledge._meta.get_field("category").null)
        self.assertTrue(
            KnowledgeCategory.objects.filter(
                organization_id=self.empty_organization_id,
                name="Без категории",
                is_system=True,
            ).exists()
        )

        classified = Knowledge.objects.get(pk=self.classified_knowledge_id)
        self.assertEqual(classified.category_id, self.custom_category_id)
        self.assertEqual(classified.visibility, "DEPARTMENTS")
        self.assertTrue(
            KnowledgeDepartment.objects.filter(knowledge_id=classified.pk).exists()
        )

        agent = AIAgent.objects.get(pk=self.agent_id)
        self.assertEqual(
            list(agent.knowledge_items.values_list("id", flat=True)),
            [self.legacy_knowledge_id],
        )
        self.assertTrue(KnowledgeAttachment.objects.filter(pk=self.attachment_id).exists())
        fragment = KnowledgeFragment.objects.get(pk=self.fragment_id)
        self.assertEqual(fragment.content, "Indexed fragment")
        self.assertEqual(
            KnowledgeFragment.objects.filter(knowledge_id=self.legacy_knowledge_id).count(),
            1,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        reversed_apps = executor.loader.project_state(self.migrate_from).apps
        ReversedKnowledge = reversed_apps.get_model("ai", "Knowledge")
        self.assertTrue(ReversedKnowledge._meta.get_field("category").null)
        reversed_knowledge = ReversedKnowledge.objects.get(pk=self.legacy_knowledge_id)
        self.assertEqual(reversed_knowledge.content, "Original content")
        self.assertIsNotNone(reversed_knowledge.category_id)
