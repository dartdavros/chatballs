# ADR-CHATBALLS-0045 (по ADR-CHATBALLS-0041 §7 «дальнейшее упрощение схемы — отдельным решением»):
# сущность `Product` удаляется целиком вместе с контуром авторизованной
# in-product поддержки — контракты, снимки личности, Product Support Token,
# виджеты режима AUTHENTICATED_PRODUCT и продукты портала.
#
# Приложения `products` и `support` удалены из кодовой базы, их исторические
# следы в миграциях других приложений вычищены, поэтому здесь снимаются
# фактические объекты БД существующих установок. На чистой установке все
# операции no-op (IF EXISTS).
#
# Данные не экспортируются — решение владельца. Диалоги, у которых личность
# жила в снимке, не удаляются: каждому создаётся контакт с именем из снимка,
# иначе они нарушили бы новый инвариант «у диалога всегда есть контакт».
from django.db import migrations

DROP_VIEWS = (
    "support_channel_directory",
    "support_conversation_directory",
)

# Порядок учитывает FK: сначала зависимые таблицы.
DROP_TABLES = (
    "support_portals_supportportalproduct",
    "support_supportidentitysnapshot",
    "support_productsupportcontract_allowed_channels",
    "support_productsupportcontract",
    "products_productdepartment",
    "products_marketplacepublication",
    "products_price",
    "products_offer",
    "identity_product",
)

DROP_COLUMNS = (
    ("channels_channel", "product_id"),
    ("channels_channel", "requires_authenticated_product_identity"),
    ("ai_llminvocation", "product_id"),
)

REMOVED_APPS = ("products", "support")

# Контакт-заглушка для диалога, чья личность жила в снимке: имя берётся из
# снимка, поэтому список диалогов остаётся читаемым.
BACKFILL_CONTACTS_SQL = """
DO $$
DECLARE
    orphan RECORD;
    new_contact_id BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations_conversation'
          AND column_name = 'support_identity_snapshot_id'
    ) THEN
        RETURN;
    END IF;

    FOR orphan IN
        SELECT DISTINCT s.id AS snapshot_id,
               s.organization_id AS organization_id,
               COALESCE(NULLIF(s.display_name, ''),
                        'Клиент ' || LEFT(s.subject_key, 8)) AS contact_name
        FROM support_supportidentitysnapshot s
        JOIN conversations_conversation c
          ON c.support_identity_snapshot_id = s.id
         AND c.contact_id IS NULL
    LOOP
        INSERT INTO conversations_contact (
            organization_id, name, phone, avatar_url,
            description, company, city, created_at
        )
        VALUES (orphan.organization_id, orphan.contact_name,
                '', '', '', '', '', NOW())
        RETURNING id INTO new_contact_id;

        UPDATE conversations_conversation
        SET contact_id = new_contact_id
        WHERE support_identity_snapshot_id = orphan.snapshot_id
          AND contact_id IS NULL;
    END LOOP;
END $$;
"""

# Виджеты личного кабинета и их браузерные сессии: режима AUTHENTICATED_PRODUCT
# больше нет, точка входа исчезает вместе с контуром.
DROP_AUTHENTICATED_WIDGETS_SQL = """
DELETE FROM webchat_websession
WHERE widget_id IN (
    SELECT id FROM webchat_webchatwidget WHERE mode = 'AUTHENTICATED_PRODUCT'
);
UPDATE support_portals_supportportal
SET widget_id = NULL
WHERE widget_id IN (
    SELECT id FROM webchat_webchatwidget WHERE mode = 'AUTHENTICATED_PRODUCT'
);
DELETE FROM webchat_webchatwidget WHERE mode = 'AUTHENTICATED_PRODUCT';
"""

# Старый XOR снимается до backfill: иначе он же и запретит проставить контакт
# диалогу, у которого ещё стоит снимок личности.
DROP_IDENTITY_XOR_SQL = """
ALTER TABLE conversations_conversation
    DROP CONSTRAINT IF EXISTS conversation_exactly_one_identity;
"""

REQUIRE_CONTACT_SQL = """
ALTER TABLE conversations_conversation
    DROP CONSTRAINT IF EXISTS conversation_requires_contact;
ALTER TABLE conversations_conversation
    ADD CONSTRAINT conversation_requires_contact CHECK (contact_id IS NOT NULL);
"""


def drop_product_support(apps, schema_editor):
    for view in DROP_VIEWS:
        schema_editor.execute(f"DROP VIEW IF EXISTS chatballs.{view}")
    schema_editor.execute(DROP_IDENTITY_XOR_SQL)
    schema_editor.execute(BACKFILL_CONTACTS_SQL)
    # Отложенные события c04-триггеров после backfill не дают выполнить ALTER —
    # прогоняем их до изменения таблицы.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    schema_editor.execute(
        "ALTER TABLE conversations_conversation "
        "DROP COLUMN IF EXISTS support_identity_snapshot_id CASCADE"
    )
    schema_editor.execute(REQUIRE_CONTACT_SQL)
    # Порядок: сперва продуктовые связи портала, иначе PROTECT-FK держит виджеты.
    schema_editor.execute(
        'DROP TABLE IF EXISTS "support_portals_supportportalproduct" CASCADE'
    )
    schema_editor.execute(DROP_AUTHENTICATED_WIDGETS_SQL)
    for table in DROP_TABLES:
        schema_editor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    for table, column in DROP_COLUMNS:
        schema_editor.execute(
            f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}" CASCADE'
        )
    apps_list = ", ".join(f"'{name}'" for name in REMOVED_APPS)
    stale_types = (
        f"SELECT id FROM django_content_type WHERE app_label IN ({apps_list}) "
        "OR (app_label = 'support_portals' AND model = 'supportportalproduct')"
    )
    schema_editor.execute(
        f"DELETE FROM django_migrations WHERE app IN ({apps_list})"
    )
    # Реестр демо-данных и журнал админки ссылаются на content type — снимаем
    # их записи до удаления самих типов.
    schema_editor.execute(
        f"DELETE FROM identity_demorecord WHERE content_type_id IN ({stale_types})"
    )
    schema_editor.execute(
        f"DELETE FROM django_admin_log WHERE content_type_id IN ({stale_types})"
    )
    schema_editor.execute(
        f"DELETE FROM auth_permission WHERE content_type_id IN ({stale_types})"
    )
    schema_editor.execute(
        f"DELETE FROM django_content_type WHERE id IN ({stale_types})"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0028_instance_settings_grants"),
        ("ai", "0016_remove_credential_mode"),
        ("channels", "0007_channel_group"),
        ("conversations", "0018_contact_merge"),
        ("support_portals", "0010_article_files"),
        ("webchat", "0004_web_chat_widget"),
    ]

    operations = [
        migrations.RunPython(drop_product_support, migrations.RunPython.noop),
    ]
