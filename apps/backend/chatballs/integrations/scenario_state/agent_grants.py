"""An explicit agent/target policy; legacy tools and skills never create it."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class AgentActionGrant(TenantRelationModel):
    tenant_relation_fields = ("agent", "integration", "scenario", "delegate")
    agent = models.ForeignKey("ai.AIAgent", on_delete=models.CASCADE, related_name="action_grants")
    integration = models.ForeignKey("integrations.Integration", null=True, on_delete=models.CASCADE)
    scenario = models.ForeignKey("integrations.ScenarioDefinition", null=True, on_delete=models.CASCADE)
    operation_key = models.CharField(max_length=100, blank=True)
    native_key = models.CharField(max_length=100, blank=True, default="")
    delegate = models.ForeignKey("identity.OrganizationMembership", null=True,
        on_delete=models.SET_NULL, related_name="delegated_agent_actions")
    mode = models.CharField(max_length=8, choices=(("off", "Off"), ("self", "Self"), ("ask", "Ask")), default="off")
    revision = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(integration__isnull=False, scenario__isnull=True, native_key="") & ~models.Q(operation_key="")
            ) | models.Q(integration__isnull=True, scenario__isnull=False, operation_key="", native_key="")
            | (models.Q(integration__isnull=True, scenario__isnull=True, operation_key="")
                & ~models.Q(native_key="")), name="agent_action_target"),
            models.UniqueConstraint(fields=("agent", "integration", "operation_key"), name="agent_operation_policy"),
            models.UniqueConstraint(fields=("agent", "scenario"), name="agent_scenario_policy"),
            models.UniqueConstraint(fields=("agent", "native_key"), condition=~models.Q(native_key=""),
                name="agent_native_policy"),
        ]
