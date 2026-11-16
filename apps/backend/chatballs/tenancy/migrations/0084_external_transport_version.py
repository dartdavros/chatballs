"""Transport configuration changes cannot revive an older reply route."""

from django.db import migrations

SQL = """
CREATE FUNCTION chatballs.external_transport_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (OLD.kind = 'MESSENGER' OR NEW.kind = 'MESSENGER') AND
       (NEW.config, NEW.secret, NEW.secret_headers, NEW.is_active, NEW.channel_id, NEW.provider)
       IS DISTINCT FROM
       (OLD.config, OLD.secret, OLD.secret_headers, OLD.is_active, OLD.channel_id, OLD.provider) THEN
        NEW.runtime_revision := OLD.runtime_revision + 1;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER external_transport_version BEFORE UPDATE ON integrations_integration
    FOR EACH ROW EXECUTE FUNCTION chatballs.external_transport_version();
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0083_external_text_runtime_guards"), ("ai", "0035_external_trigger_tombstone")]
    operations = [migrations.RunSQL(SQL, """
        DROP TRIGGER external_transport_version ON integrations_integration;
        DROP FUNCTION chatballs.external_transport_version();
    """)]
