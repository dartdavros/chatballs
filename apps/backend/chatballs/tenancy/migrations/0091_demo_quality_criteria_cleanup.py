"""Allow the demo registry to remove its unused quality criteria during a reset."""

from django.db import migrations

FORWARD = """
CREATE FUNCTION chatballs.demo_quality_criteria_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE'
        AND OLD.organization_id = chatballs.current_organization_id()
        AND EXISTS (
            SELECT 1
            FROM identity_demorecord record
            JOIN identity_demodataset dataset ON dataset.id = record.dataset_id
            JOIN django_content_type content ON content.id = record.content_type_id
            WHERE dataset.organization_id = OLD.organization_id
                AND record.organization_id = OLD.organization_id
                AND dataset.generation IS NOT NULL
                AND dataset.status IN ('REINSTALLING', 'REMOVING')
                AND content.app_label = 'conversations' AND content.model = 'qualitycriteriaversion'
                AND record.object_id = OLD.id::text
        )
        AND NOT EXISTS (
            SELECT 1 FROM conversations_qualityjob WHERE criteria_version_id = OLD.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM conversations_qualitysettings WHERE current_version_id = OLD.id
        )
    THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'Quality snapshot is immutable' USING ERRCODE = '23514';
END;
$$;
DROP TRIGGER quality_criteriaversion_immutable ON conversations_qualitycriteriaversion;
CREATE TRIGGER quality_criteriaversion_immutable BEFORE UPDATE OR DELETE
    ON conversations_qualitycriteriaversion FOR EACH ROW
    EXECUTE FUNCTION chatballs.demo_quality_criteria_immutable();
"""

REVERSE = """
DROP TRIGGER quality_criteriaversion_immutable ON conversations_qualitycriteriaversion;
CREATE TRIGGER quality_criteriaversion_immutable BEFORE UPDATE OR DELETE
    ON conversations_qualitycriteriaversion FOR EACH ROW EXECUTE FUNCTION chatballs.quality_immutable();
DROP FUNCTION chatballs.demo_quality_criteria_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0090_external_notice_guards"), ("identity", "0054_demo_shop_state")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
