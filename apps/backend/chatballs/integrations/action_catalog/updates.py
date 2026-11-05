"""Updates use their own durable state and updater, never a tenant Run."""

from chatballs.i18n import t
from chatballs.integrations.action_catalog.administrative import register
from chatballs.integrations.action_catalog.instance_schemas import field
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.updates import commands

OUTPUT = obj(update=obj(currentVersion=field("currentVersion"), latestVersion=field("latestVersion", nullable=True),
    latestName=field("latestName"), latestNotes=field("latestNotes"),
    latestPublishedAt=field("latestPublishedAt", "datetime", nullable=True), latestPageUrl=field("latestPageUrl"),
    available=field("available", "boolean"), checkedAt=field("checkedAt", "datetime", nullable=True),
    checkError=field("checkError"), updaterOnline=field("updaterOnline", "boolean"),
    install=obj(version=field("version", nullable=True), status=field("status"), message=field("message"),
        requestedAt=field("requestedAt", "datetime", nullable=True), updatedAt=field("updatedAt", "datetime", nullable=True))))


def safe_output(data):
    update = data["update"]
    if update["checkError"]:
        update["checkError"] = t("native.instance.update_failed")
    if update["install"]["message"]:
        update["install"]["message"] = t("native.instance.update_details")
    return data


for key, method, suffix, view, service, effect in (
    ("instance.update.get", "GET", "", "UpdateStateView", commands.read, Effect.READ),
    ("instance.update.check", "POST", "check/", "UpdateCheckView", commands.check, Effect.UPDATE),
    ("instance.update.install", "POST", "install/", "UpdateInstallView", commands.install, Effect.UPDATE),
):
    register(key=key, method=method, route=f"api/v1/instance/update/{suffix}", view=f"chatballs.updates.views.{view}",
        inputs=obj(), outputs=OUTPUT, service=service, audit=True, execution="io", effect=effect, project=safe_output)
