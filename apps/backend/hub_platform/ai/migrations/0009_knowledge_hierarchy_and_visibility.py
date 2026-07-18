from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0008_aiagent_credential_mode"),
        ("identity", "0015_organization_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("sort_order", models.IntegerField(default=0)),
                ("is_system", models.BooleanField(default=False)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="identity.organization",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="children",
                        to="ai.knowledgecategory",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "name", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "parent", "name"),
                        name="uniq_knowledge_category_sibling_name",
                        nulls_distinct=False,
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("is_system", True)),
                        fields=("organization",),
                        name="uniq_system_knowledge_category_per_org",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("is_system", False), ("parent__isnull", True), _connector="OR"),
                        name="system_knowledge_category_is_root",
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name="knowledge",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="knowledge_items",
                to="ai.knowledgecategory",
            ),
        ),
        migrations.AddField(
            model_name="knowledge",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("ORGANIZATION", "Organization"),
                    ("DEPARTMENTS", "Departments"),
                ],
                default="ORGANIZATION",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledge",
            constraint=models.CheckConstraint(
                condition=models.Q(("visibility__in", ["ORGANIZATION", "DEPARTMENTS"])),
                name="knowledge_visibility_valid",
            ),
        ),
        migrations.CreateModel(
            name="KnowledgeDepartment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="knowledge_links",
                        to="identity.department",
                    ),
                ),
                (
                    "knowledge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="department_links",
                        to="ai.knowledge",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="identity.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["department__name", "department_id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("knowledge", "department"),
                        name="uniq_knowledge_department",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="knowledge",
            name="departments",
            field=models.ManyToManyField(
                blank=True,
                related_name="knowledge_items",
                through="ai.KnowledgeDepartment",
                to="identity.department",
            ),
        ),
    ]
