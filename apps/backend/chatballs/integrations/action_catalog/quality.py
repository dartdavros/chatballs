"""Quality actions retain management scopes, evidence and immutable versions."""

from dataclasses import replace

from chatballs.conversations.quality import operations
from chatballs.integrations.action_catalog import quality_values
from chatballs.integrations.action_catalog.quality_schemas import (
    CRITERIA,
    JOB,
    JOBS,
    SETTINGS,
    VALUE,
)
from chatballs.integrations.action_catalog.report_schemas import FILTERS, INTEGER, PERIOD
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    TEXT,
    action,
    enum,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

JOB_ID = replace(INTEGER, required=True, title_key="native.fields.job_id")


def settings(context, values):
    return OperationResult(ResultState.COMPLETED, quality_values.settings_payload(operations.settings(context.tenant)))


def configure(context, values):
    data = dict(values)
    if "criteria" in data:
        data["criteria"] = quality_values.criteria(data["criteria"], writing=True)
    return OperationResult(ResultState.COMPLETED, quality_values.settings_payload(operations.change_settings(context.tenant, data)))


def launch(context, values):
    result = operations.launch(context.tenant, values["conversation_id"],
        {"operationId": context.effect_key, "repeat": values.get("repeat", False)})
    return OperationResult(ResultState.COMPLETED, quality_values.job_payload(result))


def history(context, values):
    result = operations.conversation_jobs(context.tenant, values["conversation_id"])
    return OperationResult(ResultState.COMPLETED, {"jobs": [quality_values.job_payload(row) for row in result["jobs"]]})


def job(context, values):
    data = operations.job(context.tenant, values["job_id"])
    context.require_conversation(data["conversationId"])
    return OperationResult(ResultState.COMPLETED, quality_values.job_payload(data))


def report(context, values):
    result = operations.report(context.tenant, values)
    return OperationResult(ResultState.COMPLETED, {**result, "jobs": [quality_values.job_payload(row) for row in result["jobs"]]})


def correct(context, values):
    job(context, values)
    data = {key: value for key, value in values.items() if key != "job_id"}
    if "value" in data:
        data["value"] = quality_values.decode(data["value"])
    return OperationResult(ResultState.COMPLETED, quality_values.job_payload(operations.correct(context.tenant, values["job_id"], data)))


def evidence(context, values):
    job(context, values)
    return OperationResult(ResultState.COMPLETED, operations.evidence(context.tenant, values["job_id"], values["message_id"]))


for key, title, inputs, output, handler, route, view, method, capability, scope in (
    ("settings.get", "native.quality_settings_read", obj(), SETTINGS, settings,
        "quality/settings/", "QualitySettingsView", "GET", "settings.manage", "organization"),
    ("settings.put", "native.quality_settings_change", obj(enabled=required(BOOLEAN), criteria=CRITERIA), SETTINGS, configure,
        "quality/settings/", "QualitySettingsView", "PUT", "settings.manage", "organization"),
    ("report.get", "native.quality_report", FILTERS, obj(period=PERIOD, jobs=JOBS), report,
        "quality/report/", "QualityReportView", "GET", "", "organization"),
    ("job.get", "native.quality_job", obj(job_id=JOB_ID), JOB, job,
        "quality/jobs/<int:job_id>/", "QualityJobView", "GET", "", "organization"),
    ("correction.post", "native.quality_correct", obj(job_id=JOB_ID, expectedRevision=required(INTEGER),
        criterionCode=required(TEXT), value=VALUE, scaleIndex=INTEGER, reason=required(TEXT)), JOB, correct,
        "quality/jobs/<int:job_id>/corrections/", "QualityCorrectionView", "POST", "", "organization"),
    ("evidence.get", "native.quality_evidence", obj(job_id=JOB_ID, message_id=required(INTEGER)),
        obj(messageId=INTEGER, conversationId=INTEGER, authorType=enum(("CONTACT", "OPERATOR", "AI"), "native.message_author"), createdAt=TypeSpec("datetime"),
            text=TEXT, contentHtml=TEXT, transcript=TEXT), evidence,
        "quality/jobs/<int:job_id>/messages/<int:message_id>/", "QualityEvidenceView", "GET", "", "organization"),
    ("conversation.get", "native.quality_history", obj(conversation_id=CONVERSATION_ID), obj(jobs=JOBS), history,
        "<int:conversation_id>/quality/", "QualityConversationView", "GET", "", "conversation"),
    ("analysis.post", "native.quality_launch", obj(conversation_id=CONVERSATION_ID, repeat=BOOLEAN), JOB, launch,
        "<int:conversation_id>/quality/launch/", "QualityLaunchView", "POST", "settings.manage", "conversation"),
):
    action(key=f"quality.{key}", title=title, input=inputs, output=output, handler=handler, capability=capability,
        scope="conversation" if handler in {job, correct, evidence} else scope,
        route=f"conversations/{route}", view=f"chatballs.conversations.quality.views.{view}", method=method)
