from django.db import migrations, models


def flip_startup_p2p_to_membership(apps, schema_editor):
    """After the constraint is widened, switch the STARTUP concurrent_p2p_calls
    grant from the provisional FIXED=3 to the membership-derived source (C07)."""
    if schema_editor.connection.alias != "default":
        return
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")
    for version in PlanVersion.objects.filter(plan__code="STARTUP"):
        QuotaGrant.objects.filter(
            plan_version=version,
            definition__key="concurrent_p2p_calls",
        ).update(limit_source="MEMBERSHIP_COUNT", limit_value=None)


def revert_startup_p2p_to_fixed(apps, schema_editor):
    if schema_editor.connection.alias != "default":
        return
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")
    for version in PlanVersion.objects.filter(plan__code="STARTUP"):
        QuotaGrant.objects.filter(
            plan_version=version,
            definition__key="concurrent_p2p_calls",
        ).update(limit_source="FIXED", limit_value=3)


class Migration(migrations.Migration):
    """C07: widen ``subscription_quota_limit_shape`` to allow the ``MEMBERSHIP_COUNT``
    limit source, then flip the STARTUP concurrent_p2p_calls grant to derive its
    limit from the active non-OWNER membership count (PLAN-CUSTOCRM-0003 §12)."""

    dependencies = [
        ("subscriptions", "0004_usagereservation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quotagrant",
            name="limit_source",
            field=models.CharField(
                choices=[
                    ("FIXED", "Fixed"),
                    ("SUBSCRIPTION_AI_AGENT_QUANTITY", "Subscription AI agent quantity"),
                    ("MEMBERSHIP_COUNT", "Active non-owner membership count"),
                ],
                default="FIXED",
                max_length=48,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="quotagrant",
            name="subscription_quota_limit_shape",
        ),
        migrations.AddConstraint(
            model_name="quotagrant",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        models.Q(("limit_value__isnull", True), ("mode", "UNLIMITED")),
                        models.Q(
                            ("limit_source", "SUBSCRIPTION_AI_AGENT_QUANTITY"),
                            ("limit_value__isnull", True),
                        ),
                        models.Q(
                            ("limit_source", "MEMBERSHIP_COUNT"),
                            ("limit_value__isnull", True),
                        ),
                        models.Q(
                            ("limit_source", "FIXED"),
                            ("limit_value__isnull", False),
                        ),
                        _connector="OR",
                    )
                ),
                name="subscription_quota_limit_shape",
            ),
        ),
        migrations.RunPython(
            flip_startup_p2p_to_membership, revert_startup_p2p_to_fixed
        ),
    ]
