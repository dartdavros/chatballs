"""Global storage commands keep their installation checks and worker protocol."""

from chatballs.i18n import t
from chatballs.integrations.action_catalog.administrative import register
from chatballs.integrations.action_catalog.instance_schemas import field
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.tenancy import storage_commands as commands

INPUT = obj(backend=field("backend"), s3Bucket=field("s3Bucket"), s3EndpointUrl=field("s3EndpointUrl"),
    s3Region=field("s3Region"), s3AccessKey=field("s3AccessKey", secret=True),
    s3SecretKey=field("s3SecretKey", secret=True), s3AddressingStyle=field("s3AddressingStyle"))
OUTPUT = obj(storage=obj(backend=field("backend"), s3Bucket=field("s3Bucket"),
    s3EndpointUrl=field("s3EndpointUrl"), s3Region=field("s3Region"),
    s3AccessKeyMasked=field("s3AccessKeyMasked"), s3HasSecretKey=field("s3HasSecretKey", "boolean"),
    s3AddressingStyle=field("s3AddressingStyle"), s3Configured=field("s3Configured", "boolean"),
    s3VerifiedAt=field("s3VerifiedAt", "datetime", nullable=True), s3LastError=field("s3LastError"),
    migration=obj(status=field("status"), total=field("total", "integer"), done=field("done", "integer"),
        error=field("error"), startedAt=field("startedAt", "datetime", nullable=True),
        finishedAt=field("finishedAt", "datetime", nullable=True)), updatedAt=field("updatedAt", "datetime", nullable=True)))


def safe_output(data):
    storage = data.get("storage")
    if storage:
        # A masked credential is not useful to automation; provider errors can
        # contain entire connection strings, including previously stored keys.
        storage["s3AccessKeyMasked"] = ""
        if storage["s3LastError"]:
            storage["s3LastError"] = t("native.instance.storage_failed")
        if storage["migration"]["error"]:
            storage["migration"]["error"] = t("native.instance.storage_failed")
    return data


for key, method, suffix, view, inputs, outputs, service, body, audit, execution, effect in (
    ("instance.storage.get", "GET", "", "StorageSettingsView", obj(), OUTPUT, commands.read, False, False, "local", Effect.READ),
    ("instance.storage.patch", "PATCH", "", "StorageSettingsView", INPUT, OUTPUT, commands.update, True, True, "io", Effect.UPDATE),
    ("instance.storage.check", "POST", "check/", "StorageCheckView", INPUT, obj(ok=field("ok", "boolean")), commands.check, True, True, "io", Effect.OTHER),
    ("instance.storage.migrate", "POST", "migrate/", "StorageMigrateView", obj(), OUTPUT, commands.migrate, False, True, "local", Effect.UPDATE),
):
    register(key=key, method=method, route=f"api/v1/instance/storage/{suffix}", view=f"chatballs.tenancy.storage_views.{view}",
        inputs=inputs, outputs=outputs, service=service, body=body, audit=audit, execution=execution, effect=effect, project=safe_output)
