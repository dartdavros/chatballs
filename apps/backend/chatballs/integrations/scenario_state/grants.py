"""Explicit employee access to a service operation; existing roles still apply."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ActionGrant(TenantRelationModel):
    tenant_relation_fields = ("integration", "membership")
    integration = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE)
    membership = models.ForeignKey("identity.OrganizationMembership", on_delete=models.CASCADE)
    operation_key = models.CharField(max_length=100)
    scope = models.CharField(max_length=16, default="conversation")
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("integration", "membership", "operation_key"), name="service_operation_grant")]
