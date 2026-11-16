"""Private file RLS, durable template generations and native cleanup ordering."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "ai_externalagentfile": (("ai_externalagentsession", "session_id"),
                             ("conversations_message", "source_message_id")),
    "ai_externalagentfilegrant": (("ai_externalagentfile", "file_id"),
                                  ("ai_externalagentrequest", "request_id")),
    "ai_externalagenttemplateversion": (),
}
SQL = """
CREATE FUNCTION chatballs.external_template_generation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    previous jsonb := '[]';
    following jsonb := '[]';
    identifier text;
    before_definition jsonb;
    after_definition jsonb;
    tenant bigint;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        previous := OLD.templates;
        tenant := OLD.organization_id;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        following := NEW.templates;
        tenant := NEW.organization_id;
    END IF;
    FOR identifier IN SELECT value->>'id' FROM jsonb_array_elements(previous)
        UNION SELECT value->>'id' FROM jsonb_array_elements(following)
    LOOP
        SELECT value INTO before_definition FROM jsonb_array_elements(previous) WHERE value->>'id' = identifier;
        SELECT value INTO after_definition FROM jsonb_array_elements(following) WHERE value->>'id' = identifier;
        IF before_definition IS DISTINCT FROM after_definition THEN
            INSERT INTO ai_externalagenttemplateversion (organization_id, template_id, revision, definition)
            VALUES (tenant, identifier, 1, COALESCE(after_definition, '{}'))
            ON CONFLICT (organization_id, template_id) DO UPDATE
            SET revision = ai_externalagenttemplateversion.revision + 1, definition = EXCLUDED.definition;
        END IF;
    END LOOP;
    RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER external_template_generation AFTER INSERT OR UPDATE OR DELETE ON ai_skill
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_template_generation();
INSERT INTO ai_externalagenttemplateversion (organization_id, template_id, revision, definition)
SELECT DISTINCT ON (organization_id, value->>'id') organization_id, value->>'id', 1, value
FROM ai_skill, jsonb_array_elements(templates) ORDER BY organization_id, value->>'id', ai_skill.id;

CREATE FUNCTION chatballs.external_file_parent_cleanup() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'ai_externalagentrequest' THEN
        DELETE FROM ai_externalagentfilegrant WHERE request_id = OLD.id;
    ELSIF TG_TABLE_NAME = 'ai_externalagentsession' THEN
        UPDATE ai_externalagentfile SET session_id = NULL WHERE session_id = OLD.id;
    ELSE
        UPDATE ai_externalagentfile SET source_message_id = NULL WHERE source_message_id = OLD.id;
    END IF;
    RETURN OLD;
END $$;
CREATE TRIGGER external_file_request_cleanup BEFORE DELETE ON ai_externalagentrequest
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_file_parent_cleanup();
CREATE TRIGGER external_file_session_cleanup BEFORE DELETE ON ai_externalagentsession
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_file_parent_cleanup();
CREATE TRIGGER external_file_message_cleanup BEFORE DELETE ON conversations_message
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_file_parent_cleanup();

CREATE FUNCTION chatballs.external_file_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.public_id, NEW.authorization_id, NEW.upload_id, NEW.upload_scope, NEW.filename, NEW.mime_type,
        NEW.size, NEW.sha256, NEW.owned, NEW.expires_at)
       IS DISTINCT FROM (OLD.public_id, OLD.authorization_id, OLD.upload_id, OLD.upload_scope, OLD.filename, OLD.mime_type,
        OLD.size, OLD.sha256, OLD.owned, OLD.expires_at)
       OR (OLD.complete AND (NOT NEW.complete OR NEW.file IS DISTINCT FROM OLD.file)) THEN
        RAISE EXCEPTION 'external_file_identity_immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_file_identity BEFORE UPDATE ON ai_externalagentfile
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_file_identity();
"""


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute(SQL)


def backwards(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER external_file_identity ON ai_externalagentfile;
        DROP FUNCTION chatballs.external_file_identity();
        DROP TRIGGER external_file_request_cleanup ON ai_externalagentrequest;
        DROP TRIGGER external_file_session_cleanup ON ai_externalagentsession;
        DROP TRIGGER external_file_message_cleanup ON conversations_message;
        DROP FUNCTION chatballs.external_file_parent_cleanup();
        DROP TRIGGER external_template_generation ON ai_skill;
        DROP FUNCTION chatballs.external_template_generation();
    """)
    for table, relations in TABLES.items():
        for _, column in relations:
            schema_editor.execute(f"DROP TRIGGER {table}_{column}_tenant ON {table}")
        schema_editor.execute(f"DROP POLICY chatballs_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY chatballs_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0085_web_schema_generation"), ("ai", "0036_external_reply_content")]
    operations = [migrations.RunPython(forwards, backwards)]
