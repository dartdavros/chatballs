# ADR-HUB-0041: удаление домена продаж. Приложения `sales` и `orders` удалены из
# кодовой базы целиком, поэтому их таблицы, ingress-вьюхи и служебные записи
# Django снимаются здесь. Данные удаляются безвозвратно — решение владельца
# зафиксировано в ADR. На чистой установке операции no-op (IF EXISTS).
from django.db import migrations

DROP_VIEWS = (
    "product_ingest_directory",
    "sales_source_directory",
)

# Порядок учитывает FK: сначала зависимые таблицы.
DROP_TABLES = (
    "orders_orderitem",
    "orders_order",
    "sales_saleevent",
    "sales_attributiontoken",
    "sales_externalcustomeridentity",
    "sales_sale",
    "sales_salessource",
)

REMOVED_APPS = ("sales", "orders")


def drop_commerce(apps, schema_editor):
    for view in DROP_VIEWS:
        schema_editor.execute(f"DROP VIEW IF EXISTS chatballs.{view}")
    for table in DROP_TABLES:
        schema_editor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    schema_editor.execute(
        "DELETE FROM django_migrations WHERE app IN ('sales', 'orders')"
    )
    schema_editor.execute(
        "DELETE FROM auth_permission WHERE content_type_id IN "
        "(SELECT id FROM django_content_type WHERE app_label IN ('sales', 'orders'))"
    )
    schema_editor.execute(
        "DELETE FROM django_content_type WHERE app_label IN ('sales', 'orders')"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0016_support_portal_widget_guards"),
    ]

    operations = [
        migrations.RunPython(drop_commerce, migrations.RunPython.noop),
    ]
