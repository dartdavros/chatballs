"""Accepted external items retain their native immutable message snapshot."""

from django.db import migrations

SQL = """
CREATE FUNCTION chatballs.external_message_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM ai_externalagentdeliveryitem WHERE message_id = OLD.id)
       AND (NEW.text, NEW.kind, NEW.content_html, NEW.format_version, NEW.presentation,
            NEW.template_snapshot, NEW.delivery_representation, NEW.attachment,
            NEW.attachment_name, NEW.attachment_content_type, NEW.attachment_size)
       IS DISTINCT FROM
           (OLD.text, OLD.kind, OLD.content_html, OLD.format_version, OLD.presentation,
            OLD.template_snapshot, OLD.delivery_representation, OLD.attachment,
            OLD.attachment_name, OLD.attachment_content_type, OLD.attachment_size) THEN
        RAISE EXCEPTION 'external_message_snapshot_immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_message_snapshot BEFORE UPDATE ON conversations_message
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_message_snapshot();
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0086_external_reply_content_guards")]
    operations = [migrations.RunSQL(SQL, """
        DROP TRIGGER external_message_snapshot ON conversations_message;
        DROP FUNCTION chatballs.external_message_snapshot();
    """)]
