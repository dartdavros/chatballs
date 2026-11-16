"""Tenant isolation, immutable snapshots/receipts, archive and deletion cleanup."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLES = {
    "ai_externalagentrequest": (("ai_externalagentsession", "session_id"),
        ("conversations_conversation", "conversation_id"), ("conversations_message", "trigger_id")),
    "ai_externalagentreceipt": (("ai_externalagentrequest", "request_id"),),
    "ai_externalagenttombstone": (("ai_externalagentconnection", "connection_id"),),
    "ai_externalagentdelivery": (("ai_externalagentrequest", "request_id"),),
    "ai_externalagentdeliveryitem": (("ai_externalagentdelivery", "delivery_id"),
        ("conversations_message", "message_id")),
}
SQL = """
CREATE FUNCTION chatballs.external_request_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.state IN ('terminal', 'cancelled') AND NEW.state <> OLD.state THEN
        RAISE EXCEPTION 'external_terminal_checkpoint_immutable' USING ERRCODE = '23514';
    END IF;
    IF (NEW.public_id, NEW.session_id, NEW.conversation_id, NEW.trigger_id,
        NEW.authorization_id, NEW.authorization_versions, NEW.sequence, NEW.deadline_at)
       IS DISTINCT FROM (OLD.public_id, OLD.session_id, OLD.conversation_id, OLD.trigger_id,
        OLD.authorization_id, OLD.authorization_versions, OLD.sequence, OLD.deadline_at) THEN
        RAISE EXCEPTION 'external_request_identity_immutable' USING ERRCODE = '23514';
    END IF;
    IF (OLD.seed_ciphertext <> '' AND NEW.seed_ciphertext NOT IN (OLD.seed_ciphertext, ''))
       OR (OLD.snapshot_ciphertext <> '' AND NEW.snapshot_ciphertext NOT IN (OLD.snapshot_ciphertext, ''))
       OR (OLD.history_ciphertext <> '' AND NEW.history_ciphertext NOT IN (OLD.history_ciphertext, ''))
       OR (OLD.snapshot_digest <> '' AND NEW.snapshot_digest <> OLD.snapshot_digest) THEN
        RAISE EXCEPTION 'external_snapshot_immutable' USING ERRCODE = '23514';
    END IF;
    IF ((OLD.seed_ciphertext <> '' AND NEW.seed_ciphertext = '')
        OR (OLD.snapshot_ciphertext <> '' AND NEW.snapshot_ciphertext = '')
        OR (OLD.history_ciphertext <> '' AND NEW.history_ciphertext = ''))
       AND (NEW.active OR NEW.terminal_at IS NULL) THEN
        RAISE EXCEPTION 'external_active_payload_required' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_request_immutable BEFORE UPDATE ON ai_externalagentrequest
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_request_immutable();
CREATE FUNCTION chatballs.external_receipt_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'ai_externalagentreceipt' THEN
        IF (NEW.request_id, NEW.result_id, NEW.digest, NEW.ack, NEW.public_id)
            IS DISTINCT FROM (OLD.request_id, OLD.result_id, OLD.digest, OLD.ack, OLD.public_id)
           OR (NEW.payload_ciphertext NOT IN (OLD.payload_ciphertext, '')) THEN
            RAISE EXCEPTION 'external_receipt_immutable' USING ERRCODE = '23514';
        END IF;
    ELSE
        IF (NEW.connection_id, NEW.request_id) IS DISTINCT FROM (OLD.connection_id, OLD.request_id)
           OR (OLD.digest <> '' AND (NEW.result_id, NEW.digest, NEW.ack)
               IS DISTINCT FROM (OLD.result_id, OLD.digest, OLD.ack)) THEN
            RAISE EXCEPTION 'external_tombstone_immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_receipt_immutable BEFORE UPDATE ON ai_externalagentreceipt
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_receipt_immutable();
CREATE TRIGGER external_tombstone_immutable BEFORE UPDATE ON ai_externalagenttombstone
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_receipt_immutable();
CREATE FUNCTION chatballs.external_conversation_cleanup() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM ai_externalagentdeliveryitem WHERE delivery_id IN (
            SELECT d.id FROM ai_externalagentdelivery d JOIN ai_externalagentrequest r
            ON r.id = d.request_id WHERE r.conversation_id = OLD.id);
        DELETE FROM ai_externalagentdelivery WHERE request_id IN (
            SELECT id FROM ai_externalagentrequest WHERE conversation_id = OLD.id);
        DELETE FROM ai_externalagentreceipt WHERE request_id IN (
            SELECT id FROM ai_externalagentrequest WHERE conversation_id = OLD.id);
        DELETE FROM ai_externalagentrequest WHERE conversation_id = OLD.id;
        DELETE FROM ai_externalagentsession WHERE conversation_id = OLD.id;
        RETURN OLD;
    END IF;
    IF NEW.archived_at IS NOT NULL AND OLD.archived_at IS NULL THEN
        UPDATE ai_externalagentrequest SET state = CASE WHEN state = 'terminal' THEN state ELSE 'cancelled' END,
            active = false, terminal_at = COALESCE(terminal_at, now()),
            cancel_pending = attempts > 0, lease_until = NULL,
            seed_ciphertext = '', snapshot_ciphertext = '', history_ciphertext = ''
            WHERE conversation_id = NEW.id;
        UPDATE ai_externalagentreceipt SET payload_ciphertext = '' WHERE request_id IN (
            SELECT id FROM ai_externalagentrequest WHERE conversation_id = NEW.id);
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_conversation_cleanup BEFORE DELETE OR UPDATE ON conversations_conversation
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_conversation_cleanup();
"""


def forwards(apps, schema_editor):
    for table, relations in TABLES.items():
        schema_editor.execute(guards.FORWARD_RLS.format(table=table))
        for parent, column in relations:
            schema_editor.execute(guards.FORWARD_TRIGGER.format(table=table, parent=parent, column=column))
    schema_editor.execute(SQL)


def backwards(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER external_conversation_cleanup ON conversations_conversation;
        DROP FUNCTION chatballs.external_conversation_cleanup();
        DROP TRIGGER external_request_immutable ON ai_externalagentrequest;
        DROP FUNCTION chatballs.external_request_immutable();
        DROP TRIGGER external_receipt_immutable ON ai_externalagentreceipt;
        DROP TRIGGER external_tombstone_immutable ON ai_externalagenttombstone;
        DROP FUNCTION chatballs.external_receipt_immutable();
    """)
    for table, relations in TABLES.items():
        for _, column in relations:
            schema_editor.execute(f"DROP TRIGGER {table}_{column}_tenant ON {table}")
        schema_editor.execute(f"DROP POLICY chatballs_tenant_isolation ON {table}")
        schema_editor.execute(f"DROP POLICY chatballs_schema_access ON {table}")
        schema_editor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0082_external_route_revocation"), ("ai", "0033_external_text_runtime")]
    operations = [migrations.RunPython(forwards, backwards)]
