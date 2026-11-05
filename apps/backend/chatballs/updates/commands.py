"""Explicit installation update commands; the updater protocol is unchanged."""
from django.db import transaction

from chatballs.identity.audit import record_audit_event
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.integrations.action_catalog.authority import require_instance
from chatballs.updates.models import UpdateState
from chatballs.updates.services import (
    InstallNotPossible,
    check_for_updates,
    request_install,
    sync_install_status,
    update_payload,
)


def read(user, *, request=None):
    user = require_instance(user, read=True)
    state = sync_install_status(UpdateState.load())
    return CommandOutcome({"update": update_payload(state)})


def check(user, *, request=None):
    user = require_instance(user)
    state = sync_install_status(check_for_updates(force=True))
    return CommandOutcome({"update": update_payload(state)})


@transaction.atomic
def install(user, *, request=None):
    user = require_instance(user)
    try:
        state = UpdateState.load()
        state = UpdateState.objects.select_for_update().get(pk=state.pk)
        state = request_install(actor=user, state=state)
    except InstallNotPossible as error:
        return CommandOutcome({"detail": str(error), "code": error.code}, status=409)
    record_audit_event(
        action="updates.install_requested",
        actor=user,
        organization=None,
        object_type="UpdateState",
        object_id=state.install_version,
        payload={"version": state.install_version},
        request=request,
    )
    return CommandOutcome({"update": update_payload(state)}, status=202)
