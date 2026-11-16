"""Tenant-scoped employee facts, independently of private recovery records."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "ai_externalagentnotice"


def forwards(apps, schema_editor):
    schema_editor.execute(guards.FORWARD_RLS.format(table=TABLE))
    schema_editor.execute(guards.FORWARD_TRIGGER.format(
        table=TABLE, parent="conversations_conversation", column="conversation_id"))


def backwards(apps, schema_editor):
    schema_editor.execute("""
        DROP TRIGGER ai_externalagentnotice_conversation_id_tenant ON ai_externalagentnotice;
        DROP POLICY chatballs_tenant_isolation ON ai_externalagentnotice;
        DROP POLICY chatballs_schema_access ON ai_externalagentnotice;
        ALTER TABLE ai_externalagentnotice DISABLE ROW LEVEL SECURITY;
    """)


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0089_external_test_scope_guards"), ("ai", "0039_externalagentnotice")]
    operations = [migrations.RunPython(forwards, backwards)]
