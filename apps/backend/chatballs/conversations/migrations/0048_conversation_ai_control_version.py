from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conversations", "0047_message_reply_snapshot")]
    operations = [migrations.AddField(model_name="conversation", name="ai_control_version",
        field=models.PositiveBigIntegerField(default=0, db_default=0, editable=False)),
        migrations.RunSQL("""
            CREATE FUNCTION chatballs.bump_ai_control_version() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                NEW.ai_control_version := OLD.ai_control_version;
                IF NEW.control_mode IS DISTINCT FROM OLD.control_mode
                    OR NEW.assigned_operator_id IS DISTINCT FROM OLD.assigned_operator_id
                    OR NEW.channel_id IS DISTINCT FROM OLD.channel_id
                    OR NEW.lifecycle IS DISTINCT FROM OLD.lifecycle
                    OR NEW.archived_at IS DISTINCT FROM OLD.archived_at THEN
                    NEW.ai_control_version := OLD.ai_control_version + 1;
                END IF;
                RETURN NEW;
            END $$;
            ALTER FUNCTION chatballs.bump_ai_control_version() OWNER TO chatballs_schema;
            REVOKE ALL ON FUNCTION chatballs.bump_ai_control_version() FROM PUBLIC;
            CREATE TRIGGER conversation_ai_control_version BEFORE UPDATE ON conversations_conversation
                FOR EACH ROW EXECUTE FUNCTION chatballs.bump_ai_control_version();
        """, """
            DROP TRIGGER conversation_ai_control_version ON conversations_conversation;
            DROP FUNCTION chatballs.bump_ai_control_version();
        """)]
