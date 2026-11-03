"""Entity extensions must resolve to real, correctly classified operations."""

from chatballs.integrations.adapters.contracts import READ_EFFECTS, Effect


def validate_entity(adapter, entity):
    errors = []
    reference = entity.references
    if reference:
        operation = adapter.operation(reference.operation)
        if not operation or operation.effect not in READ_EFFECTS or not callable(reference.arguments) or not callable(reference.candidates):
            errors.append(f"entity {entity.key}: invalid reference search")
    binding = entity.synchronization
    if binding:
        read = adapter.operation(binding.read_operation)
        if not read or read.effect not in READ_EFFECTS or not callable(binding.read_arguments) or not callable(binding.snapshot):
            errors.append(f"entity {entity.key}: invalid synchronization read")
        for key, callback, effect in ((binding.update_operation, binding.update_arguments, Effect.UPDATE),
                                      (binding.delete_operation, binding.delete_arguments, Effect.DELETE)):
            if key or callback:
                operation = adapter.operation(key)
                if operation is None or operation.effect != effect or not callable(callback):
                    errors.append(f"entity {entity.key}: invalid synchronization write")
    return errors
