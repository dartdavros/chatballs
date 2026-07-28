from django.db import migrations
from django.db.models import Max
from django.utils import timezone


def _clone_with_unlimited_portals(
    PlanVersion,
    EntitlementGrant,
    QuotaGrant,
    source,
    definition,
):
    next_version = (
        PlanVersion.objects.filter(plan_id=source.plan_id).aggregate(Max("version"))[
            "version__max"
        ]
        + 1
    )
    replacement = PlanVersion.objects.create(
        plan_id=source.plan_id,
        version=next_version,
        agent_unit_price_minor=source.agent_unit_price_minor,
        currency=source.currency,
        billing_period=source.billing_period,
        fixed_ai_agent_quantity=source.fixed_ai_agent_quantity,
        effective_from=timezone.now(),
        transition_rules=source.transition_rules,
    )
    EntitlementGrant.objects.bulk_create(
        [
            EntitlementGrant(
                plan_version=replacement,
                definition_id=grant.definition_id,
                enabled=grant.enabled,
            )
            for grant in EntitlementGrant.objects.filter(plan_version=source)
        ]
    )
    QuotaGrant.objects.bulk_create(
        [
            QuotaGrant(
                plan_version=replacement,
                definition_id=grant.definition_id,
                mode="UNLIMITED" if grant.definition_id == definition.id else grant.mode,
                limit_source=grant.limit_source,
                limit_value=None if grant.definition_id == definition.id else grant.limit_value,
                window_seconds=grant.window_seconds,
            )
            for grant in QuotaGrant.objects.filter(plan_version=source)
        ]
    )
    replacement.published_at = timezone.now()
    replacement.save(update_fields=["published_at"])
    return replacement


def remove_support_portal_limit(apps, schema_editor):
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    EntitlementGrant = apps.get_model("subscriptions", "EntitlementGrant")
    QuotaDefinition = apps.get_model("subscriptions", "QuotaDefinition")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")
    Subscription = apps.get_model("subscriptions", "Subscription")
    definition = QuotaDefinition.objects.filter(key="support_portals").first()
    if definition is None:
        return

    source_ids = list(
        QuotaGrant.objects.filter(definition=definition)
        .exclude(mode="UNLIMITED")
        .values_list("plan_version_id", flat=True)
    )
    for source in PlanVersion.objects.filter(id__in=source_ids):
        if source.published_at is None:
            QuotaGrant.objects.filter(
                plan_version=source,
                definition=definition,
            ).update(mode="UNLIMITED", limit_value=None, window_seconds=None)
            continue
        replacement = _clone_with_unlimited_portals(
            PlanVersion,
            EntitlementGrant,
            QuotaGrant,
            source,
            definition,
        )
        Subscription.objects.filter(plan_version=source).update(
            plan_version=replacement
        )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0009_support_portal_plan_grants")]
    operations = [
        migrations.RunPython(
            remove_support_portal_limit,
            migrations.RunPython.noop,
        ),
    ]
