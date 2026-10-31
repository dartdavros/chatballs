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
               "arguments": step.definition.get("arguments", {})}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def approved(step, run):
    return (step.approval_expires_at is not None and step.approval_expires_at > timezone.now()
            and hmac.compare_digest(step.confirmed_digest, invocation_digest(step, run)))
