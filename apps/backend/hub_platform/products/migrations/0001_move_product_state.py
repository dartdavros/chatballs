import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("identity", "0004_employeeprofile_phone")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Product",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                        ),
                        ("code", models.SlugField(max_length=64)),
                        ("name", models.CharField(max_length=255)),
                        (
                            "status",
                            models.CharField(
                                choices=[("ACTIVE", "Активен"), ("DISABLED", "Неактивен")],
                                default="ACTIVE",
                                max_length=32,
                            ),
                        ),
                        ("site_url", models.URLField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "organization",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.PROTECT,
                                related_name="products",
                                to="identity.organization",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "identity_product",
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("organization", "code"),
                                name="uniq_product_org_code",
                            )
                        ],
                    },
                )
            ],
        )
    ]
