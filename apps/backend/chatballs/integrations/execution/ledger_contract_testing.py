"""Second independently registered contract, confined to automatic tests."""

from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    Effect,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    Presentation,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.schema import TypeSpec


def read(context, operation, arguments):
    return OperationResult(ResultState.COMPLETED, data={"value": arguments["value"] + ":ledger"})


ADAPTER = AdapterDescriptor(key="ledger", contract_version=1, listed=False,
    presentation=Presentation("", "", "", "", "", ""),
    auth_methods=(AuthMethod("public", "none@1", "", TypeSpec("object")),),
    operations=(OperationDescriptor("project", "runs.operation", Effect.READ,
        TypeSpec("object", properties=(("value", TypeSpec("string", required=True)),)),
        TypeSpec("object", properties=(("value", TypeSpec("string", required=True)),)),
        OperationHandlers(execute=read), retry=RetryStrategy.SAFE_READ),))
