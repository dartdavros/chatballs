from django.db import migrations

# Approved quotas are stored as a unified dict so each grant is described by a
# single tuple of (mode, limit_source, limit_value, window_seconds). This keeps
# the seed readable regardless of whether a quota is a fixed cap, a rate window,
# a concurrent ceiling, or unlimited. Unapproved quotas stay absent.
#
# storage_bytes values use binary units (MiB/GiB).

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

_MIB = 1024 * 1024
_GIB = 1024 * 1024 * 1024


def _fixed(value):
    return ("HARD", "FIXED", value, None)


def _unlimited():
    return ("UNLIMITED", "FIXED", None, None)


def _concurrent(value):
    return ("CONCURRENT", "FIXED", value, None)


def _rate(value, window_seconds):
    return ("RATE", "FIXED", value, window_seconds)


def _ai_slots():
    return ("HARD", "SUBSCRIPTION_AI_AGENT_QUANTITY", None, None)


# Quotas approved by the owner on 2026-07-15 for Free/Startup publication.
# concurrent_p2p_calls is a provisional minimum for Startup; deriving it from the
# active membership count is a separate C07 decision (see PLAN-CUSTOCRM-0003 §12).
PLAN_SPECS = {
    "FREE": {
        "name": "Бесплатный",
        "saleable": True,
        "price": 0,
        "fixed_quantity": 1,
        "entitlements": ("managed_ai", "byok_ai"),
        "quotas": {
            "ai_agent_slots": _ai_slots(),
            "products": _fixed(1),
            "client_connections": _fixed(3),
            "new_dialogs_per_period": _fixed(500),
            "managed_ai_credits": _fixed(300),
            "storage_bytes": _fixed(500 * _MIB),
            # No CRM API / calls / voice entitlement on Free -> gated to zero.
            "crm_api_requests_per_window": _fixed(0),
            "concurrent_p2p_calls": _concurrent(0),
            "concurrent_voice_sessions": _concurrent(0),
        },
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
        "quotas": {
            "ai_agent_slots": _ai_slots(),
            "products": _unlimited(),
            "client_connections": _unlimited(),
            "new_dialogs_per_period": _unlimited(),
            "managed_ai_credits": _fixed(1000),
            "storage_bytes": _fixed(2 * _GIB),
            "crm_api_requests_per_window": _rate(60, 60),
            "concurrent_p2p_calls": _concurrent(3),
            "concurrent_voice_sessions": _concurrent(10),
        },
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
        "quotas": {
            "ai_agent_slots": _ai_slots(),
        },
    },
    "CORPORATION": {
        "name": "Корпорация",
        "saleable": False,
        "price": 990_000,
        "fixed_quantity": None,
        "entitlements": ENTITLEMENTS,
        "quotas": {
            "ai_agent_slots": _ai_slots(),
        },
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
        QuotaGrant.objects.bulk_create(
            [
                QuotaGrant(
                    plan_version=version,
                    definition=quota_definitions[key],
                    mode=mode,
                    limit_source=limit_source,
                    limit_value=limit_value,
                    window_seconds=window_seconds,
                )
                for key, (mode, limit_source, limit_value, window_seconds) in spec["quotas"].items()
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
