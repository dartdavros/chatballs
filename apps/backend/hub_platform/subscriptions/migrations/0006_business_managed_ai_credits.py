from django.db import migrations


def add_business_managed_ai_credits(apps, schema_editor):
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    QuotaDefinition = apps.get_model("subscriptions", "QuotaDefinition")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")

    version = PlanVersion.objects.get(plan__code="BUSINESS", version=1)
    definition = QuotaDefinition.objects.get(key="managed_ai_credits")
    QuotaGrant.objects.create(
        plan_version=version,
        definition=definition,
        mode="HARD",
        limit_source="FIXED",
        limit_value=3000,
        window_seconds=None,
    )


def remove_business_managed_ai_credits(apps, schema_editor):
    apps.get_model("subscriptions", "QuotaGrant").objects.filter(
        plan_version__plan__code="BUSINESS",
        plan_version__version=1,
        definition__key="managed_ai_credits",
        mode="HARD",
        limit_source="FIXED",
        limit_value=3000,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0005_membership_count_limit"),
    ]

    operations = [
        migrations.RunPython(
            add_business_managed_ai_credits,
            remove_business_managed_ai_credits,
        ),
    ]
