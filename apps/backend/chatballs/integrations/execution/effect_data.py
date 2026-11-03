"""Reserve bounded response capacity before send, then account persisted values."""

from chatballs.integrations.execution.budgets import account_data, size
from chatballs.integrations.scenario_state.steps import ScenarioStep


def account_effect(run, step, *, terminal=False):
    if not run.definition.get("composite"):
        return
    old = ScenarioStep.objects.only("content").get(pk=step.pk).definition
    values = step.definition
    reserved = old.get("_responseReservation", 0)
    release = 0
    if terminal:
        values.pop("_responseReservation", None)
        release = reserved
    elif reserved:
        # Pending continuation consumes the capacity reserved before send.
        # Counting both it and the whole reservation can reject a sent result.
        previous = {key: value for key, value in old.items() if key != "_responseReservation"}
        current = {key: value for key, value in values.items() if key != "_responseReservation"}
        remaining = max(0, reserved - (size(current) - size(previous)))
        values["_responseReservation"] = remaining
        release = reserved - remaining
    account_data(run, size(values) - size(old) - release)
    step.definition = values
