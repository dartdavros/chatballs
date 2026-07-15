from django.db import migrations


TENANT_FOREIGN_KEYS = (
    ("identity_employeeprofile", "identity_department", "primary_department_id"),
    ("identity_accessprofilecapability", "identity_accessprofile", "access_profile_id"),
    ("identity_employeeaccessassignment", "identity_employeeprofile", "employee_id"),
    ("identity_employeeaccessassignment", "identity_accessprofile", "access_profile_id"),
    ("identity_employeeaccessassignment", "identity_department", "department_id"),
    ("identity_employeeaccessassignment", "identity_employeeprofile", "assigned_by_id"),
    ("identity_organizationinvitation", "identity_employeeprofile", "created_by_id"),
    ("products_productdepartment", "identity_product", "product_id"),
    ("products_productdepartment", "identity_department", "department_id"),
    ("products_offer", "identity_product", "product_id"),
    ("products_offer", "products_offer", "primary_box_offer_id"),
    ("products_price", "products_offer", "offer_id"),
    ("products_marketplacepublication", "products_price", "price_id"),
    ("ai_knowledgeattachment", "ai_knowledge", "knowledge_id"),
    ("ai_knowledgefragment", "ai_knowledge", "knowledge_id"),
    ("ai_aiagent", "channels_channel", "channel_id"),
    ("ai_llminvocation", "channels_channel", "channel_id"),
    ("ai_llminvocation", "identity_product", "product_id"),
    ("integrations_integration", "channels_channel", "channel_id"),
    ("channels_channel", "identity_department", "department_id"),
    ("channels_channel", "identity_product", "product_id"),
    ("channels_channel", "integrations_integration", "provider_integration_id"),
    ("conversations_connectionidentity", "conversations_contact", "contact_id"),
    ("conversations_connectionidentity", "integrations_integration", "connection_id"),
    ("conversations_conversation", "channels_channel", "channel_id"),
    ("conversations_conversation", "integrations_integration", "connection_id"),
    ("conversations_conversation", "conversations_contact", "contact_id"),
    ("conversations_conversation", "support_supportidentitysnapshot", "support_identity_snapshot_id"),
    ("conversations_conversation", "conversations_conversation", "previous_conversation_id"),
    ("conversations_conversationread", "conversations_conversation", "conversation_id"),
    ("conversations_message", "conversations_conversation", "conversation_id"),
    ("orders_order", "conversations_contact", "contact_id"),
    ("orders_order", "conversations_conversation", "conversation_id"),
    ("orders_order", "identity_product", "product_id"),
    ("orders_order", "channels_channel", "channel_id"),
    ("orders_orderitem", "orders_order", "order_id"),
    ("orders_orderitem", "products_offer", "offer_id"),
    ("orders_orderitem", "products_price", "price_id"),
    ("sales_salessource", "identity_product", "product_id"),
    ("sales_sale", "identity_product", "product_id"),
    ("sales_sale", "sales_salessource", "sales_source_id"),
    ("sales_sale", "conversations_contact", "contact_id"),
    ("sales_sale", "conversations_conversation", "conversation_id"),
    ("sales_sale", "sales_saleevent", "last_event_id"),
    ("sales_saleevent", "sales_salessource", "sales_source_id"),
    ("sales_saleevent", "sales_sale", "sale_id"),
    ("sales_attributiontoken", "identity_product", "product_id"),
    ("sales_attributiontoken", "products_offer", "offer_id"),
    ("sales_attributiontoken", "conversations_contact", "contact_id"),
    ("sales_attributiontoken", "conversations_conversation", "conversation_id"),
    ("sales_attributiontoken", "channels_channel", "channel_id"),
    ("sales_attributiontoken", "integrations_integration", "connection_id"),
    ("sales_externalcustomeridentity", "identity_product", "product_id"),
    ("sales_externalcustomeridentity", "conversations_contact", "contact_id"),
    ("support_productsupportcontract", "identity_product", "product_id"),
    ("support_supportidentitysnapshot", "identity_product", "product_id"),
    ("support_supportidentitysnapshot", "support_productsupportcontract", "contract_id"),
    ("calls_callsession", "conversations_conversation", "conversation_id"),
    ("calls_callsession", "integrations_integration", "delivery_connection_id"),
    ("calls_callinvite", "calls_callsession", "call_session_id"),
    ("calls_callinvite", "conversations_connectionidentity", "connection_identity_id"),
    ("calls_callparticipant", "calls_callsession", "call_session_id"),
    ("calls_callparticipant", "conversations_connectionidentity", "connection_identity_id"),
    ("calls_callmetric", "calls_callsession", "call_session_id"),
    ("notifications_notification", "identity_department", "department_id"),
    ("notifications_notificationread", "notifications_notification", "notification_id"),
    ("notifications_messengerbinding", "integrations_integration", "integration_id"),
    ("notifications_messengerbindingcode", "integrations_integration", "integration_id"),
    ("webchat_websession", "integrations_integration", "connection_id"),
    ("webchat_websession", "conversations_connectionidentity", "identity_id"),
    ("events_outboxevent", "identity_employeeprofile", "membership_id"),
)

TENANT_USER_FIELDS = (
    ("conversations_conversation", "assigned_operator_id"),
    ("conversations_conversationread", "user_id"),
    ("conversations_message", "author_user_id"),
    ("calls_callsession", "initiated_by_id"),
    ("calls_callparticipant", "user_id"),
    ("notifications_notification", "recipient_user_id"),
    ("notifications_notificationread", "user_id"),
    ("notifications_messengerbinding", "user_id"),
    ("notifications_messengerbindingcode", "user_id"),
    ("sales_saleevent", "actor_user_id"),
)

TENANT_PAIRS = (
    ("ai_aiagent_knowledge_items", "ai_aiagent", "aiagent_id", "ai_knowledge", "knowledge_id"),
    ("support_productsupportcontract_allowed_channels", "support_productsupportcontract", "productsupportcontract_id", "channels_channel", "channel_id"),
)


def add_constraints(apps, schema_editor):
    schema_editor.execute("CREATE SCHEMA IF NOT EXISTS custocrm")
    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION custocrm.enforce_tenant_fk() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE parent_org bigint; fk_value text;
        BEGIN
            fk_value := to_jsonb(NEW) ->> TG_ARGV[1];
            IF fk_value IS NULL THEN RETURN NEW; END IF;
            EXECUTE format('SELECT organization_id FROM %%s WHERE id::text = $1', TG_ARGV[0]::regclass)
                INTO parent_org USING fk_value;
            IF parent_org IS DISTINCT FROM NEW.organization_id THEN
                RAISE EXCEPTION 'cross-tenant relation on %%.%%', TG_TABLE_NAME, TG_ARGV[1];
            END IF;
            RETURN NEW;
        END $$;

        CREATE OR REPLACE FUNCTION custocrm.enforce_tenant_user() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE user_value text;
        BEGIN
            user_value := to_jsonb(NEW) ->> TG_ARGV[0];
            IF user_value IS NULL THEN RETURN NEW; END IF;
            IF NOT EXISTS (
                SELECT 1 FROM identity_employeeprofile membership
                WHERE membership.user_id::text = user_value
                  AND membership.organization_id = NEW.organization_id
            ) THEN
                RAISE EXCEPTION 'tenant user has no membership on %%.%%', TG_TABLE_NAME, TG_ARGV[0];
            END IF;
            RETURN NEW;
        END $$;

        CREATE OR REPLACE FUNCTION custocrm.enforce_tenant_pair() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE left_org bigint; right_org bigint; left_value text; right_value text;
        BEGIN
            left_value := to_jsonb(NEW) ->> TG_ARGV[1];
            right_value := to_jsonb(NEW) ->> TG_ARGV[3];
            EXECUTE format('SELECT organization_id FROM %%s WHERE id::text = $1', TG_ARGV[0]::regclass)
                INTO left_org USING left_value;
            EXECUTE format('SELECT organization_id FROM %%s WHERE id::text = $1', TG_ARGV[2]::regclass)
                INTO right_org USING right_value;
            IF left_org IS DISTINCT FROM right_org THEN
                RAISE EXCEPTION 'cross-tenant many-to-many relation on %%', TG_TABLE_NAME;
            END IF;
            RETURN NEW;
        END $$;
        """
    )
    with schema_editor.connection.cursor() as cursor:
        for index, (child, parent, fk_column) in enumerate(TENANT_FOREIGN_KEYS):
            cursor.execute(
                f"SELECT EXISTS (SELECT 1 FROM {child} child JOIN {parent} parent "
                f"ON parent.id = child.{fk_column} WHERE child.{fk_column} IS NOT NULL "
                "AND child.organization_id IS DISTINCT FROM parent.organization_id)"
            )
            if cursor.fetchone()[0]:
                raise RuntimeError(f"C04 preflight: cross-tenant relation {child}.{fk_column}")
            schema_editor.execute(
                f"CREATE CONSTRAINT TRIGGER c04_tfk_{index} AFTER INSERT OR UPDATE ON {child} "
                "DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION "
                f"custocrm.enforce_tenant_fk('{parent}', '{fk_column}')"
            )
        for index, (table, user_column) in enumerate(TENANT_USER_FIELDS):
            cursor.execute(
                f"SELECT EXISTS (SELECT 1 FROM {table} item WHERE item.{user_column} IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM identity_employeeprofile membership "
                f"WHERE membership.user_id = item.{user_column} "
                "AND membership.organization_id = item.organization_id))"
            )
            if cursor.fetchone()[0]:
                raise RuntimeError(f"C04 preflight: tenant user mismatch {table}.{user_column}")
            schema_editor.execute(
                f"CREATE CONSTRAINT TRIGGER c04_tuser_{index} AFTER INSERT OR UPDATE ON {table} "
                "DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION "
                f"custocrm.enforce_tenant_user('{user_column}')"
            )
        for index, (table, left_table, left_column, right_table, right_column) in enumerate(TENANT_PAIRS):
            cursor.execute(
                f"SELECT EXISTS (SELECT 1 FROM {table} link "
                f"JOIN {left_table} left_item ON left_item.id = link.{left_column} "
                f"JOIN {right_table} right_item ON right_item.id = link.{right_column} "
                "WHERE left_item.organization_id IS DISTINCT FROM right_item.organization_id)"
            )
            if cursor.fetchone()[0]:
                raise RuntimeError(f"C04 preflight: cross-tenant relation in {table}")
            schema_editor.execute(
                f"CREATE CONSTRAINT TRIGGER c04_tpair_{index} AFTER INSERT OR UPDATE ON {table} "
                "DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION "
                f"custocrm.enforce_tenant_pair('{left_table}', '{left_column}', "
                f"'{right_table}', '{right_column}')"
            )


def remove_constraints(apps, schema_editor):
    for index, (table, _parent, _column) in enumerate(TENANT_FOREIGN_KEYS):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS c04_tfk_{index} ON {table}")
    for index, (table, _column) in enumerate(TENANT_USER_FIELDS):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS c04_tuser_{index} ON {table}")
    for index, (table, *_rest) in enumerate(TENANT_PAIRS):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS c04_tpair_{index} ON {table}")
    schema_editor.execute("DROP FUNCTION IF EXISTS custocrm.enforce_tenant_pair()")
    schema_editor.execute("DROP FUNCTION IF EXISTS custocrm.enforce_tenant_user()")
    schema_editor.execute("DROP FUNCTION IF EXISTS custocrm.enforce_tenant_fk()")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0001_initial"),
        ("identity", "0014_alter_accessprofilecapability_organization_and_more"),
        ("products", "0010_alter_marketplacepublication_organization_and_more"),
        ("ai", "0006_alter_aiagent_organization_and_more"),
        ("integrations", "0002_integration_channel_integration_poll_marker"),
        ("channels", "0004_remove_channel_ai_fields"),
        ("conversations", "0006_alter_connectionidentity_organization_and_more"),
        ("orders", "0004_alter_orderitem_organization"),
        ("sales", "0002_employee_actor_type"),
        ("support", "0002_alter_productsupportcontract_code"),
        ("calls", "0004_alter_callinvite_organization_and_more"),
        ("notifications", "0006_alter_messengerbinding_organization_and_more"),
        ("webchat", "0003_alter_websession_organization"),
        ("events", "0004_inboxevent_organization_inboxevent_ownership_and_more"),
    ]
    operations = [migrations.RunPython(add_constraints, remove_constraints)]
