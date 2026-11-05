"""Server-owned files and resource scope for every native domain invocation."""

from chatballs.integrations.action_catalog.contracts import NativeContext
from chatballs.integrations.adapters.file_access import file_opener
from chatballs.integrations.adapters.files import file_store
from chatballs.integrations.execution.files import file_references


def context_for(run, step, action, actor, scope, arguments):
    store = file_store(context=actor, integration=None, step=step)

    def bounded_store(name, content_type, stream, size):
        if type(size) is not int or size < 0 or size > action.operation.limits.max_file_bytes:
            raise ValueError("file_size_mismatch")
        return store(name, content_type, stream, size)

    return NativeContext(actor, str(step.effect_key), str(run.public_id), step.path,
        open_file=file_opener(actor.organization_id,
            allowed=file_references(action.operation.input, arguments), max_bytes=action.operation.limits.max_file_bytes),
        store_file=bounded_store, scope=scope, conversation_id=run.conversation_id,
        contact_id=run.definition.get("context", {}).get("contact", {}).get("id"),
        max_file_bytes=action.operation.limits.max_file_bytes)
