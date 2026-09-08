from django.db import migrations


VIEWS = {
    "membership_directory": """
        SELECT membership.id AS resource_id,
               membership.organization_id,
               membership.user_id,
               membership.totp_required,
               membership.blocked_at
        FROM identity_employeeprofile membership
    """,
    # Вьюхи product_ingest_directory/sales_source_directory удалены вместе с
    # доменом продаж (ADR-CHATBALLS-0041); на старых БД их снимает 0017_drop_commerce.
    "attachment_directory": """
        SELECT attachment.id AS resource_id,
               attachment.organization_id,
               attachment.public_id::text AS lookup_key
        FROM ai_knowledgeattachment attachment
    """,
    "call_invite_directory": """
        SELECT invite.id::text AS resource_id,
               invite.organization_id,
               invite.token_hash AS lookup_key
        FROM calls_callinvite invite
    """,
    "call_session_directory": """
        SELECT call.id::text AS resource_id,
               call.organization_id,
               call.id::text AS lookup_key
        FROM calls_callsession call
    """,
    "web_session_directory": """
        SELECT session.id AS resource_id,
               session.organization_id,
               session.token_hash AS lookup_key
        FROM webchat_websession session
    """,
    "web_channel_directory": """
        SELECT integration.id AS resource_id,
               integration.organization_id,
               channel.code AS lookup_key
        FROM integrations_integration integration
        JOIN channels_channel channel ON channel.id = integration.channel_id
        WHERE integration.provider = 'WEB' AND channel.is_active
    """,
    # Вьюхи support_channel_directory/support_conversation_directory удалены
    # вместе с сущностью Product и авторизованным in-product чатом
    # (ADR-CHATBALLS-0045); на старых БД их снимает 0029_drop_product_support.
}


def create_views(apps, schema_editor):
    for name, query in VIEWS.items():
        schema_editor.execute(
            f"CREATE OR REPLACE VIEW chatballs.{name} WITH (security_barrier = true) AS {query}"
        )
        schema_editor.execute(f"ALTER VIEW chatballs.{name} OWNER TO chatballs_schema")
        schema_editor.execute(f"REVOKE ALL ON chatballs.{name} FROM PUBLIC")
        schema_editor.execute(
            f"GRANT SELECT ON chatballs.{name} TO chatballs_runtime_platform"
        )


def drop_views(apps, schema_editor):
    for name in reversed(VIEWS):
        schema_editor.execute(f"DROP VIEW IF EXISTS chatballs.{name}")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0003_rls_policies")]
    operations = [migrations.RunPython(create_views, drop_views)]
