"""Journal administration never launches or approves another execution."""

from functools import partial

from chatballs.integrations.action_catalog.scenarios import invoke
from chatballs.integrations.action_catalog.schema import action, enum, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.execution import journal_queries
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.retention import policy_for, update_policy
from chatballs.integrations.execution.retention_views import policy_payload
from chatballs.tenancy.database import tenant_atomic


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.run_fields.{name}", **kwargs)


def listing(tenant, data):
    return journal_queries.listing(tenant, {key: str(value) for key, value in data.items()})


def retention(tenant):
    with tenant_atomic(tenant):
        journal_queries.require_manager(tenant)
        return policy_payload(policy_for(tenant))


def retention_update(tenant, data):
    return policy_payload(update_policy(tenant, step_days=data["stepDays"], journal_days=data["journalDays"],
        version=data["version"], confirmed=data.get("confirmed", False)))


def without_edit_tokens(value):
    if isinstance(value, dict):
        return {key: without_edit_tokens(child) for key, child in value.items() if key != "editToken"}
    if isinstance(value, list):
        return [without_edit_tokens(child) for child in value]
    return value


def detail(tenant, public_id):
    return without_edit_tokens(journal_queries.detail(tenant, public_id))


def change(tenant, data):
    # Confirmation, editing and repeat remain their own signed invocation
    # protocols. A nested native operation cannot mint a new launch principal.
    with tenant_atomic(tenant):
        run = control(tenant=tenant, public_id=data["public_id"], action=data["action"], path=data.get("path"))
        return without_edit_tokens({"run": run_payload(run, detail=True, tenant=tenant)})


IDENTITY = field("run", required=True)
RUN = obj(run=field("run", "json"))
RETENTION = obj(stepDays=field("stepDays", "integer"), journalDays=field("journalDays", "integer"),
    version=field("version", "integer"), effectiveAt=field("effectiveAt", "datetime", nullable=True))
FILTERS = obj(**{key: field(key) for key in ("conversation", "q", "state", "group", "initiator", "period", "connection", "before", "page")})
LIST = obj(items=field("runs", "array", items=TypeSpec("json")), count=field("count", "integer"),
    page=field("page", "integer"), pageSize=field("pageSize", "integer"), filters=field("filters", "json"))
CONTROL = obj(public_id=IDENTITY, action=required(enum(("cancel", "reconcile"), "native.run_control")), path=field("path"))

for key, method, route, view, inputs, outputs, service, arguments, body, effect in (
    ("runs.get", "GET", "runs/", "views.RunListView", FILTERS, LIST, listing, (), True, Effect.READ),
    ("runs.detail.get", "GET", "runs/<uuid:public_id>/", "views.RunDetailView", obj(public_id=IDENTITY), RUN,
        detail, ("public_id",), False, Effect.READ),
    ("runs.control.post", "POST", "runs/<uuid:public_id>/<str:action>/", "views.RunControlView", CONTROL, RUN,
        change, (), True, Effect.UPDATE),
    ("runs.retention.get", "GET", "runs/retention/", "retention_views.RunRetentionView", obj(), RETENTION,
        retention, (), False, Effect.READ),
    ("runs.retention.put", "PUT", "runs/retention/", "retention_views.RunRetentionView",
        obj(stepDays=field("stepDays", "integer", required=True), journalDays=field("journalDays", "integer", required=True),
            version=field("version", "integer", required=True), confirmed=field("confirmed", "boolean")), RETENTION,
        retention_update, (), True, Effect.UPDATE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, arguments=arguments, body=body),
        capability="", scope="organization", route=f"integrations/{route}",
        view=f"chatballs.integrations.execution.{view}", method=method, effect=effect)
