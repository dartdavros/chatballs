from django.db import migrations


ENTITLEMENTS = (
    "sales_department",
    "support_department",
    "crm_api",
    "product_sales_api",
    "p2p_calls",
    "voice_ai",
    "knowledge_base",
    "one_c_connector",
    "customer_audit",
    "sso_saml",
    "managed_ai",
    "byok_ai",
)

QUOTAS = {
    "ai_agent_slots": "slots",
    "products": "items",
    "client_connections": "connections",
    "new_dialogs_per_period": "dialogs",
    "managed_ai_credits": "credits",
    "storage_bytes": "bytes",
    "crm_api_requests_per_window": "requests",
    "concurrent_p2p_calls": "calls",
    "concurrent_voice_sessions": "sessions",
    "audit_retention_days": "days",
}

PLAN_SPECS = {
    "FREE": {
        "name": "Бесплатный",
        "saleable": True,
        "price": 0,
        "fixed_quantity": 1,
        "entitlements": ("managed_ai", "byok_ai"),
        "fixed_quotas": {
            "products": 1,
            "client_connections": 3,
            "new_dialogs_per_period": 500,
        },
        "unlimited_quotas": (),
    },
    "STARTUP": {
        "name": "Стартап",
        "saleable": True,
        "price": 290_000,
        "fixed_quantity": None,
        "entitlements": (
            "sales_department",
            "support_department",
            "crm_api",
            "product_sales_api",
            "p2p_calls",
            "voice_ai",
            "knowledge_base",
            "managed_ai",
            "byok_ai",
        ),
        "fixed_quotas": {},
        "unlimited_quotas": (
            "products",
            "client_connections",
            "new_dialogs_per_period",
        ),
    },
    "BUSINESS": {
        "name": "Бизнес",
        "saleable": False,
        "price": 490_000,
        "fixed_quantity": None,
        "entitlements": (
            "sales_department",
            "support_department",
            "crm_api",
            "product_sales_api",
            "p2p_calls",
            "voice_ai",
            "knowledge_base",
            "one_c_connector",
            "managed_ai",
            "byok_ai",
        ),
        "fixed_quotas": {},
        "unlimited_quotas": (
            "products",
            "client_connections",
            "new_dialogs_per_period",
        ),
    },
    "CORPORATION": {
        "name": "Корпорация",
        "saleable": False,
        "price": 990_000,
        "fixed_quantity": None,
        "entitlements": ENTITLEMENTS,
        "fixed_quotas": {},
        "unlimited_quotas": (
            "products",
            "client_connections",
            "new_dialogs_per_period",
        ),
    },
}


def seed_plan_drafts(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    PlanVersion = apps.get_model("subscriptions", "PlanVersion")
    EntitlementDefinition = apps.get_model("subscriptions", "EntitlementDefinition")
    EntitlementGrant = apps.get_model("subscriptions", "EntitlementGrant")
    QuotaDefinition = apps.get_model("subscriptions", "QuotaDefinition")
    QuotaGrant = apps.get_model("subscriptions", "QuotaGrant")

    entitlement_definitions = {
        key: EntitlementDefinition.objects.create(key=key, name=key.replace("_", " ").title())
        for key in ENTITLEMENTS
    }
    quota_definitions = {
        key: QuotaDefinition.objects.create(
            key=key,
            name=key.replace("_", " ").title(),
            unit=unit,
        )
        for key, unit in QUOTAS.items()
    }
    for code, spec in PLAN_SPECS.items():
        plan = Plan.objects.create(
            code=code,
            name=spec["name"],
            saleable=spec["saleable"],
        )
        version = PlanVersion.objects.create(
            plan=plan,
            version=1,
            agent_unit_price_minor=spec["price"],
            currency="RUB",
            billing_period="MONTH",
            fixed_ai_agent_quantity=spec["fixed_quantity"],
        )
        EntitlementGrant.objects.bulk_create(
            [
                EntitlementGrant(
                    plan_version=version,
                    definition=entitlement_definitions[key],
                    enabled=True,
                )
                for key in spec["entitlements"]
            ]
        )
        QuotaGrant.objects.create(
            plan_version=version,
            definition=quota_definitions["ai_agent_slots"],
            mode="HARD",
            limit_source="SUBSCRIPTION_AI_AGENT_QUANTITY",
        )
        QuotaGrant.objects.bulk_create(
            [
                QuotaGrant(
                    plan_version=version,
                    definition=quota_definitions[key],
                    mode="HARD",
                    limit_source="FIXED",
                    limit_value=value,
                )
                for key, value in spec["fixed_quotas"].items()
            ]
            + [
                QuotaGrant(
                    plan_version=version,
                    definition=quota_definitions[key],
                    mode="UNLIMITED",
                    limit_source="FIXED",
                )
                for key in spec["unlimited_quotas"]
            ]
        )


def remove_plan_drafts(apps, schema_editor):
    apps.get_model("subscriptions", "Plan").objects.filter(
        code__in=PLAN_SPECS
    ).delete()
    apps.get_model("subscriptions", "EntitlementDefinition").objects.filter(
        key__in=ENTITLEMENTS
    ).delete()
    apps.get_model("subscriptions", "QuotaDefinition").objects.filter(
        key__in=QUOTAS
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [migrations.RunPython(seed_plan_drafts, remove_plan_drafts)]
