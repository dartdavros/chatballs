"""Safe journal: codes and identifiers only, no arguments or remote text."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class RunJournalEntry(TenantRelationModel):
    tenant_relation_fields = ("run",)
    run = models.ForeignKey("integrations.ScenarioRun", on_delete=models.CASCADE, related_name="journal")
    code = models.CharField(max_length=64)
    path = models.CharField(max_length=512, blank=True)
    attempt = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=("run", "id"), name="scenario_journal_page")]
