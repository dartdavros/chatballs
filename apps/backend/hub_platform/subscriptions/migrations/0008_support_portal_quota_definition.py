from django.db import migrations


def add_support_portal_quota_definition(apps, schema_editor):
    QuotaDefinition = apps.get_model("subscriptions", "QuotaDefinition")
    QuotaDefinition.objects.get_or_create(
        key="support_portals",
        defaults={"name": "Support portals", "unit": "portals"},
    )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0007_quota_accounting_and_reservation_quantity")]
    operations = [
        migrations.RunPython(
            add_support_portal_quota_definition,
            migrations.RunPython.noop,
        ),
    ]
