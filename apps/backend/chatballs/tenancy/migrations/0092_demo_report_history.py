"""Import historical support facts only for conversations owned by the demo seed."""

from importlib import import_module

from django.db import migrations

_ORIGINAL = import_module("chatballs.tenancy.migrations.0043_domain_event_guards").FACT_INSERT
_FUNCTION = _ORIGINAL.split("CREATE TRIGGER domain_event_prepare", 1)[0].replace(
    "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1,
)
_DEMO_TIMESTAMPS = """
    IF COALESCE(current_setting('chatballs.demo_report_generation', true), '') = '' OR NOT EXISTS (
        SELECT 1 FROM identity_demorecord record
        JOIN identity_demodataset dataset ON dataset.id = record.dataset_id
        JOIN django_content_type content ON content.id = record.content_type_id
        JOIN conversations_conversation dialog ON dialog.id = NEW.conversation_id
        WHERE dataset.organization_id = NEW.organization_id
            AND record.organization_id = NEW.organization_id
            AND dataset.generation::text = current_setting('chatballs.demo_report_generation', true)
            AND dataset.status IN ('INSTALLING', 'REINSTALLING')
            AND content.app_label = 'conversations' AND content.model = 'conversation'
            AND record.object_id = NEW.conversation_id::text
            AND NEW.occurred_at BETWEEN dialog.created_at AND clock_timestamp()
    ) THEN
        NEW.occurred_at := clock_timestamp();
    END IF;
"""


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0091_demo_quality_criteria_cleanup")]
    operations = [migrations.RunSQL(
        _FUNCTION.replace("    NEW.occurred_at := clock_timestamp();\n", _DEMO_TIMESTAMPS),
        _FUNCTION,
    )]
