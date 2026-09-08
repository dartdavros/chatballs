# ADR-CHATBALLS-0042 §2: тарифный контур удалён целиком. Приложение `subscriptions`
# (планы, подписки, entitlements, quotas, usage-биллинг, reservations) снято из
# кодовой базы — его таблицы и служебные записи Django дропаются здесь.
# Данные удаляются безвозвратно — решение владельца зафиксировано в ADR.
# На чистой установке операции no-op (IF EXISTS).
from django.db import migrations

# Порядок учитывает FK: сначала зависимые таблицы.
DROP_TABLES = (
    "subscriptions_usagereservation",
    "subscriptions_usageledgerentry",
    "subscriptions_usagecounter",
    "subscriptions_usageperiod",
    "subscriptions_subscriptionoverride",
    "subscriptions_subscription",
    "subscriptions_quotagrant",
    "subscriptions_entitlementgrant",
    "subscriptions_quotadefinition",
    "subscriptions_entitlementdefinition",
    "subscriptions_planversion",
    "subscriptions_plan",
)


def drop_billing(apps, schema_editor):
    for table in DROP_TABLES:
        schema_editor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    schema_editor.execute(
        "DELETE FROM django_migrations WHERE app = 'subscriptions'"
    )
    schema_editor.execute(
        "DELETE FROM auth_permission WHERE content_type_id IN "
        "(SELECT id FROM django_content_type WHERE app_label = 'subscriptions')"
    )
    schema_editor.execute(
        "DELETE FROM django_content_type WHERE app_label = 'subscriptions'"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0019_support_portal_directory_without_department"),
    ]

    operations = [
        migrations.RunPython(drop_billing, migrations.RunPython.noop),
    ]
