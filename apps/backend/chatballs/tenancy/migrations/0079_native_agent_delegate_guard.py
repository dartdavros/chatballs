"""Retain forced RLS and enforce the new delegate's organization at the DB boundary."""

from importlib import import_module

from django.db import migrations

guards = import_module("chatballs.tenancy.migrations.0068_service_connection_guards")
TABLE = "integrations_agentactiongrant"


def forwards(apps, schema_editor):
    parent = apps.get_model("identity", "OrganizationMembership")._meta.db_table
    schema_editor.execute(guards.FORWARD_TRIGGER.format(table=TABLE,
        parent=parent, column="delegate_id"))


def backwards(apps, schema_editor):
    schema_editor.execute(f"DROP TRIGGER {TABLE}_delegate_id_tenant ON {TABLE}")


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0078_merge_native_receipt_guards"),
        ("integrations", "0032_native_agent_delegates")]
    operations = [migrations.RunPython(forwards, backwards)]
