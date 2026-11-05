"""Signed consent carries only a digest, never operational values."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from django.core import signing
from django.utils import timezone

from chatballs.integrations.execution.permissions import ExecutionDenied

SALT = "service-execution-plan-v1"
LIFETIME = timedelta(minutes=15)


def plan_digest(tenant, plan):
    value = {"organization": tenant.organization_id, "actor": tenant.membership_id, "plan": plan}
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def sign_plan(tenant, plan):
    return signing.dumps({"digest": plan_digest(tenant, plan), "expires": (timezone.now() + LIFETIME).timestamp()}, salt=SALT)


def verify_plan(tenant, plan, token):
    try:
        signed = signing.loads(token, salt=SALT, max_age=LIFETIME.total_seconds())
        if not hmac.compare_digest(signed["digest"], plan_digest(tenant, plan)) or signed["expires"] <= timezone.now().timestamp():
            raise ValueError
        return datetime.fromtimestamp(signed["expires"], tz=UTC)
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        raise ExecutionDenied("approval_changed") from None
