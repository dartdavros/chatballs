"""Tenant and immutable ownership boundaries for private external test sessions."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "ai_externalagenttestsession"
SQL = """
CREATE FUNCTION chatballs.external_test_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND ((NEW.organization_id, NEW.owner_id, NEW.agent_id, NEW.conversation_id,
        NEW.public_id, NEW.context_ciphertext) IS DISTINCT FROM
        (OLD.organization_id, OLD.owner_id, OLD.agent_id, OLD.conversation_id, OLD.public_id, OLD.context_ciphertext)
        OR (OLD.closed_at IS NOT NULL AND NEW.closed_at IS DISTINCT FROM OLD.closed_at)) THEN
        RAISE EXCEPTION 'external_test_scope_immutable' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM conversations_conversation c JOIN ai_aiagent a ON a.channel_id = c.channel_id
        WHERE c.id = NEW.conversation_id AND a.id = NEW.agent_id AND c.is_test
            AND c.organization_id = NEW.organization_id AND a.organization_id = NEW.organization_id)
       OR (TG_OP = 'INSERT' AND NOT EXISTS (SELECT 1 FROM identity_employeeprofile m
        WHERE m.organization_id = NEW.organization_id AND m.user_id = NEW.owner_id
            AND m.role IN ('OWNER', 'ADMIN') AND m.blocked_at IS NULL)) THEN
        RAISE EXCEPTION 'external_test_scope_invalid' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_test_scope_guard BEFORE INSERT OR UPDATE ON ai_externalagenttestsession
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_test_scope_guard();
CREATE FUNCTION chatballs.conversation_test_audience_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.is_test IS DISTINCT FROM OLD.is_test THEN
        RAISE EXCEPTION 'conversation_test_audience_immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER conversation_test_audience_guard BEFORE UPDATE ON conversations_conversation
    FOR EACH ROW EXECUTE FUNCTION chatballs.conversation_test_audience_guard();
"""


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    for parent, column in [("ai_aiagent", "agent_id"), ("conversations_conversation", "conversation_id")]:
        schema_editor.execute(guards.FORWARD_TRIGGER.format(table=TABLE, parent=parent, column=column))
    schema_editor.execute(SQL)


def backwards(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER conversation_test_audience_guard ON conversations_conversation;
        DROP FUNCTION chatballs.conversation_test_audience_guard();
        DROP TRIGGER external_test_scope_guard ON ai_externalagenttestsession;
        DROP FUNCTION chatballs.external_test_scope_guard();
        DROP TRIGGER ai_externalagenttestsession_agent_id_tenant ON ai_externalagenttestsession;
        DROP TRIGGER ai_externalagenttestsession_conversation_id_tenant ON ai_externalagenttestsession;
        DROP POLICY chatballs_tenant_isolation ON ai_externalagenttestsession;
        DROP POLICY chatballs_schema_access ON ai_externalagenttestsession;
        ALTER TABLE ai_externalagenttestsession DISABLE ROW LEVEL SECURITY;
    """)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0088_external_operation_guards"),
                    ("ai", "0038_externalagentbinding_accepted_definitions_and_more"),
                    ("conversations", "0049_remove_conversation_conversation_requires_contact_and_more")]
    operations = [migrations.RunPython(forwards, backwards)]
