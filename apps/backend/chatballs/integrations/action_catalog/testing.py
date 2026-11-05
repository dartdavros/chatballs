"""Run a confirmed native action through the public launch service in tests."""

from uuid import uuid4

from chatballs.integrations.execution.launch import launch_direct
from chatballs.integrations.execution.runner import run_one
from chatballs.tenancy.database import tenant_atomic


def execute_action(tenant, key, arguments, *, conversation_id=None):
    trigger = str(uuid4())
    kwargs = dict(tenant=tenant, connection_id="chatballs", operation_key=key,
        arguments=arguments, trigger_key=trigger, conversation_id=conversation_id)
    preview, _ = launch_direct(**kwargs, preview=True)
    run, _ = launch_direct(**kwargs, confirmation=preview["confirmation"])
    run_one(tenant, run.public_id)
    with tenant_atomic(tenant):
        run.refresh_from_db()
        return run, run.steps.get().definition.get("result")
