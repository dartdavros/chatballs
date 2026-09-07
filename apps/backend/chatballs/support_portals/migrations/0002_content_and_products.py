import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0005_enforce_policy_invariants"),
        ("support_portals", "0001_portals"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalArticle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=96)),
                ("locale", models.CharField(default="ru", max_length=16)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Черновик"),
                            ("PUBLISHED", "Опубликована"),
                            ("ARCHIVED", "Архив"),
                        ],
                        default="DRAFT",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="articles",
                        to="support_portals.portalcategory",
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
                (
                    "portal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="articles",
                        to="support_portals.supportportal",
                    ),
                ),
            ],
            options={"ordering": ["slug", "id"]},
        ),
        migrations.CreateModel(
            name="PortalArticleRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision", models.PositiveIntegerField()),
                ("title", models.CharField(max_length=255)),
                ("summary", models.CharField(blank=True, max_length=500)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revisions",
                        to="support_portals.portalarticle",
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
            options={"ordering": ["-revision"]},
        ),
        migrations.AddField(
            model_name="portalarticle",
            name="published_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="support_portals.portalarticlerevision",
            ),
        ),
        migrations.CreateModel(
            name="PortalArticleFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("helpful", models.BooleanField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="support_portals.portalarticle",
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
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="portalarticle",
            constraint=models.UniqueConstraint(
                fields=("portal", "locale", "slug"),
                name="uniq_support_portal_article_slug",
            ),
        ),
        migrations.AddConstraint(
            model_name="portalarticle",
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=["DRAFT", "PUBLISHED", "ARCHIVED"]),
                name="support_portal_article_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="portalarticlerevision",
            constraint=models.UniqueConstraint(
                fields=("article", "revision"),
                name="uniq_support_portal_article_revision",
            ),
        ),
        migrations.AddConstraint(
            model_name="portalarticlerevision",
            constraint=models.CheckConstraint(
                condition=models.Q(revision__gt=0),
                name="support_portal_article_revision_positive",
            ),
        ),
    ]
