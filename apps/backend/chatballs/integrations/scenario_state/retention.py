"""Organization policy; shortening is optimistic, confirmed and delayed."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ScenarioRetentionPolicy(TenantRelationModel):
    # One policy per organization; no operational payload is kept here.
    version = models.PositiveIntegerField(default=1)
    step_days = models.PositiveIntegerField(default=7)
    journal_days = models.PositiveIntegerField(default=30)
    previous_step_days = models.PositiveIntegerField(default=7)
    previous_journal_days = models.PositiveIntegerField(default=30)
    effective_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organization",), name="scenario_retention_org"),
            models.CheckConstraint(condition=models.Q(step_days__lte=models.F("journal_days")), name="scenario_retention_order"),
        ]


class StepOperationalFile(TenantRelationModel):
    tenant_relation_fields = ("step", "file")
    step = models.ForeignKey("integrations.ScenarioStep", on_delete=models.CASCADE, related_name="operational_files")
    file = models.ForeignKey("integrations.ServiceFile", on_delete=models.CASCADE, related_name="execution_owners")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("step", "file"), name="scenario_step_file")]
