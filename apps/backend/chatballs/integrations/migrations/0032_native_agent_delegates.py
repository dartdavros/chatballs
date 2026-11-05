"""Extend explicit agent targets without granting or inferring any authority."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0031_native_operation_files")]
    operations = [
        migrations.RemoveConstraint(model_name="agentactiongrant", name="agent_action_target"),
        migrations.AddField(model_name="agentactiongrant", name="native_key",
            field=models.CharField(blank=True, default="", max_length=100)),
        migrations.AddField(model_name="agentactiongrant", name="delegate",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="delegated_agent_actions", to="identity.organizationmembership")),
        migrations.AddConstraint(model_name="agentactiongrant", constraint=models.CheckConstraint(condition=(
            models.Q(integration__isnull=False, scenario__isnull=True, native_key="") & ~models.Q(operation_key="")
        ) | models.Q(integration__isnull=True, scenario__isnull=False, operation_key="", native_key="")
        | (models.Q(integration__isnull=True, scenario__isnull=True, operation_key="")
            & ~models.Q(native_key="")), name="agent_action_target")),
        migrations.AddConstraint(model_name="agentactiongrant", constraint=models.UniqueConstraint(
            fields=("agent", "native_key"), condition=~models.Q(native_key=""), name="agent_native_policy")),
    ]
