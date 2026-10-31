"""A shared connection lane across existing worker replicas."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ConnectionExecutionLane(TenantRelationModel):
    tenant_relation_fields = ("integration", "step")
    integration = models.OneToOneField("integrations.Integration", on_delete=models.CASCADE)
    step = models.ForeignKey("integrations.ScenarioStep", null=True, on_delete=models.SET_NULL)
    until = models.DateTimeField(null=True)
    cooldown_until = models.DateTimeField(null=True)
