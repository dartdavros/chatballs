from django.db import migrations, models

SQL = """
CREATE FUNCTION chatballs.external_trigger_digest_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.trigger_digest IS DISTINCT FROM OLD.trigger_digest THEN
        RAISE EXCEPTION 'external_trigger_digest_immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_trigger_digest_immutable BEFORE UPDATE ON ai_externalagenttombstone
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_trigger_digest_immutable();
CREATE FUNCTION chatballs.external_delivery_archive() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.archived_at IS NULL AND NEW.archived_at IS NOT NULL THEN
        UPDATE ai_externalagentdeliveryitem SET
            state = CASE WHEN sending THEN 'unknown' ELSE 'suppressed' END,
            reason_code = 'control_revoked', sending = false
            WHERE state = 'queued' AND delivery_id IN (
                SELECT d.id FROM ai_externalagentdelivery d JOIN ai_externalagentrequest r
                ON r.id = d.request_id WHERE r.conversation_id = NEW.id);
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_delivery_archive BEFORE UPDATE ON conversations_conversation
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_delivery_archive();
"""


class Migration(migrations.Migration):
    dependencies = [("ai", "0034_external_processing_mode"), ("tenancy", "0083_external_text_runtime_guards")]
    operations = [migrations.AddField(
        model_name="externalagenttombstone", name="trigger_digest",
        field=models.CharField(max_length=64, default=""), preserve_default=False,
    ), migrations.RunSQL(SQL, """
        DROP TRIGGER external_delivery_archive ON conversations_conversation;
        DROP FUNCTION chatballs.external_delivery_archive();
        DROP TRIGGER external_trigger_digest_immutable ON ai_externalagenttombstone;
        DROP FUNCTION chatballs.external_trigger_digest_immutable();
    """)]
