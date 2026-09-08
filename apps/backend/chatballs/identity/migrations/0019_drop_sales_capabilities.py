# ADR-CHATBALLS-0041: домен продаж удалён — capabilities sales.* исключаются из
# реестра. Строки профилей с этими кодами удаляются до установки нового
# check-constraint, иначе constraint невыполним на существующих данных.
from django.db import migrations, models

REMOVED = ("sales.view", "sales.operate", "sales.correct", "sales_sources.manage")

ALLOWED = [
    "company.view",
    "company.manage",
    "departments.view",
    "departments.manage",
    "employees.view",
    "employees.manage",
    "products.view",
    "products.manage",
    "channels.view",
    "channels.manage",
    "ai.view",
    "ai.manage",
    "ai.publish",
    "integrations.view",
    "integrations.manage",
    "secrets.manage",
    "settings.view",
    "settings.manage",
    "audit.view",
    "conversations.view",
    "conversations.operate",
    "conversations.call",
    "customers.view",
    "customers.manage",
    "support.view",
    "support.operate",
    "notifications.manage",
]


def drop_sales_capability_rows(apps, schema_editor):
    AccessProfileCapability = apps.get_model("identity", "AccessProfileCapability")
    AccessProfileCapability.objects.filter(capability_code__in=REMOVED).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0018_organization_branding_db_defaults"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="accessprofilecapability",
            name="access_profile_capability_registry",
        ),
        migrations.RunPython(drop_sales_capability_rows, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="accessprofilecapability",
            constraint=models.CheckConstraint(
                condition=models.Q(("capability_code__in", ALLOWED)),
                name="access_profile_capability_registry",
            ),
        ),
    ]
