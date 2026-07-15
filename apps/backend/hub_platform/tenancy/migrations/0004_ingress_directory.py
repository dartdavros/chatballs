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
    "product_ingest_directory": """
        SELECT product.id AS resource_id,
               product.organization_id,
               product.ingest_token_hash AS lookup_key
        FROM identity_product product
        WHERE product.ingest_token_hash <> ''
    """,
    "sales_source_directory": """
        SELECT source.id AS resource_id,
               source.organization_id,
               source.credential_hash AS lookup_key
        FROM sales_salessource source
        WHERE source.credential_hash <> '' AND source.status = 'ACTIVE'
    """,
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
    "support_channel_directory": """
        SELECT channel.id AS resource_id,
               channel.organization_id,
               channel.code AS lookup_key,
               product.support_token_secret
        FROM channels_channel channel
        JOIN identity_product product ON product.id = channel.product_id
        WHERE channel.is_active
    """,
    "support_conversation_directory": """
        SELECT conversation.id AS resource_id,
               conversation.organization_id,
               conversation.support_identity_snapshot_id AS snapshot_id
        FROM conversations_conversation conversation
        WHERE conversation.support_identity_snapshot_id IS NOT NULL
    """,
}


def create_views(apps, schema_editor):
    for name, query in VIEWS.items():
        schema_editor.execute(
            f"CREATE OR REPLACE VIEW custocrm.{name} WITH (security_barrier = true) AS {query}"
        )
        schema_editor.execute(f"ALTER VIEW custocrm.{name} OWNER TO custocrm_schema")
        schema_editor.execute(f"REVOKE ALL ON custocrm.{name} FROM PUBLIC")
        schema_editor.execute(
            f"GRANT SELECT ON custocrm.{name} TO custocrm_runtime_platform"
        )


def drop_views(apps, schema_editor):
    for name in reversed(VIEWS):
        schema_editor.execute(f"DROP VIEW IF EXISTS custocrm.{name}")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0003_rls_policies")]
    operations = [migrations.RunPython(create_views, drop_views)]
