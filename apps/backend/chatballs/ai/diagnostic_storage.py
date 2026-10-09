"""Diagnostic persistence must not roll back the customer's reply."""

import logging
from functools import wraps

from django.db import transaction

from chatballs.ai.diagnostic_models import TurnDiagnostic

logger = logging.getLogger(__name__)
RETAINED_TURNS = 20


def isolated_capture(function):
    @wraps(function)
    def capture(*args, **kwargs):
        try:
            # A savepoint keeps the enclosing turn transaction usable after a DB error.
            with transaction.atomic():
                return function(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 - diagnostics cannot block the reply
            logger.warning("Diagnostic capture failed: %s", type(error).__name__)
            return None
    return capture


def prune_diagnostics(message):
    traces = TurnDiagnostic.objects.filter(
        organization_id=message.organization_id, message__conversation_id=message.conversation_id,
    )
    recent = traces.order_by("-message_id").values_list("id", flat=True)[:RETAINED_TURNS]
    traces.exclude(id__in=recent).delete()
