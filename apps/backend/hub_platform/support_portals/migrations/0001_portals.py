import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("identity", "0016_channel_capabilities")]

    operations = [
        migrations.CreateModel(
            name="SupportPortal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("default_locale", models.CharField(default="ru", max_length=16)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Черновик"),
                            ("PUBLISHED", "Опубликован"),
                            ("ARCHIVED", "Архив"),
                        ],
                        default="DRAFT",
                        max_length=16,
                    ),
                ),
                ("transition_version", models.PositiveIntegerField(default=0)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="support_portals",
                        to="identity.department",
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
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="PortalCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("sort_order", models.PositiveIntegerField(default=0)),
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
                        to="support_portals.portalcategory",
                    ),
                ),
                (
                    "portal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categories",
                        to="support_portals.supportportal",
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="supportportal",
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "PUBLISHED", "ARCHIVED"]),
                name="support_portal_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="portalcategory",
            constraint=models.UniqueConstraint(
                fields=("portal", "slug"),
                name="uniq_support_portal_category_slug",
            ),
        ),
    ]
