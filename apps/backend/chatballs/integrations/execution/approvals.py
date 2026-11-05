"""Approval is for one immutable invocation, context and expiry."""

import hashlib
import hmac
import json

from django.utils import timezone


def invocation_digest(step, run):
    payload = {"run": str(run.public_id), "path": step.path,
               "effect": str(step.effect_key), "operation": step.operation_key,
               "version": step.adapter_version, "connection": step.integration_id,
               "context": run.definition.get("context", {}),
               "ai": run.definition.get("ai", {}),
               "arguments": step.definition.get("arguments", {})}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def approved(step, run):
    if run.definition.get("ai"):
        from chatballs.identity.models import OrganizationMembership
        from chatballs.integrations.execution.ai_policy import approver
        from chatballs.integrations.execution.permissions import ExecutionDenied
        from chatballs.tenancy.context import TenantContext
        member = OrganizationMembership.objects.select_related("organization", "user").filter(
            pk=step.definition.get("approvedBy"), organization_id=run.organization_id).first()
        if member is None:
            return False
        try:
            approver(TenantContext.for_membership(member), run)
        except ExecutionDenied:
            return False
    return (step.approval_expires_at is not None and step.approval_expires_at > timezone.now()
            and hmac.compare_digest(step.confirmed_digest, invocation_digest(step, run)))
