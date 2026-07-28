from django.db import migrations
from django.db.models import Max
from django.utils import timezone


LIMITS = {
    "FREE": None,
    "STARTUP": None,
    "BUSINESS": None,
    "CORPORATION": None,
}


def _add_grant(QuotaGrant, version, definition, limit):
    QuotaGrant.objects.get_or_create(
        plan_version=version,
        definition=definition,
        defaults={
            "mode": "UNLIMITED" if limit is None else "HARD",
            "limit_source": "FIXED",
            "limit_value": limit,
            "window_seconds": None,
        },
    )


def add_support_portal_plan_grants(apps, schema_editor):
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    EntitlementGrant = apps.get_model("subscriptions", "EntitlementGrant")
    QuotaDefinition = apps.get_model("subscriptions", "QuotaDefinition")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")
    Subscription = apps.get_model("subscriptions", "Subscription")

    definition = QuotaDefinition.objects.get(key="support_portals")
    published_sources = []
    for version in PlanVersion.objects.select_related("plan").order_by("plan_id", "version"):
        if version.plan.code not in LIMITS:
            continue
        if QuotaGrant.objects.filter(
            plan_version=version,
            definition=definition,
        ).exists():
            continue
        if version.published_at is None:
            _add_grant(
                QuotaGrant,
                version,
                definition,
                LIMITS[version.plan.code],
            )
        else:
            published_sources.append(version)

    for source in published_sources:
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
                    mode=grant.mode,
                    limit_source=grant.limit_source,
                    limit_value=grant.limit_value,
                    window_seconds=grant.window_seconds,
                )
                for grant in QuotaGrant.objects.filter(plan_version=source)
            ]
        )
        _add_grant(
            QuotaGrant,
            replacement,
            definition,
            LIMITS[source.plan.code],
        )
        replacement.published_at = timezone.now()
        replacement.save(update_fields=["published_at"])
        Subscription.objects.filter(plan_version=source).update(
            plan_version=replacement
        )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0008_support_portal_quota_definition")]
    operations = [
        migrations.RunPython(
            add_support_portal_plan_grants,
            migrations.RunPython.noop,
        ),
    ]
