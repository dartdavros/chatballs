"""Advance the WEB generation in the definition transaction, including A→B→A."""

from django.db import migrations

SQL = """
CREATE FUNCTION chatballs.web_schema_generation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.provider = 'WEB' OR NEW.provider = 'WEB' THEN
        IF (NEW.config->'fields', NEW.provider, NEW.is_active, NEW.channel_id)
            IS DISTINCT FROM
           (OLD.config->'fields', OLD.provider, OLD.is_active, OLD.channel_id) THEN
            NEW.web_schema_generation := OLD.web_schema_generation + 1;
        ELSE
            NEW.web_schema_generation := OLD.web_schema_generation;
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER web_schema_generation BEFORE UPDATE ON integrations_integration
    FOR EACH ROW EXECUTE FUNCTION chatballs.web_schema_generation();
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0084_external_transport_version"),
                    ("integrations", "0036_web_schema_generation")]
    operations = [migrations.RunSQL(SQL, """
        DROP TRIGGER web_schema_generation ON integrations_integration;
        DROP FUNCTION chatballs.web_schema_generation();
    """)]
