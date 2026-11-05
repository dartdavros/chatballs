"""Notification actions always operate on the initiating employee's profile."""

from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    IDENTIFIER,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec
from chatballs.notifications import profile_services as service

STRINGS = TypeSpec("array", items=TEXT)
TRANSPORT = TypeSpec("enum", options=(EnumOption("BROWSER", "native.transport_browser"),
    EnumOption("MESSENGER", "native.transport_messenger")))
AVAILABLE = TypeSpec("array", items=obj(code=TEXT, label=TEXT))
PREFERENCE = obj(transport=TRANSPORT, enabled=BOOLEAN, types=STRINGS, availableTypes=AVAILABLE)
NOTIFICATION = obj(id=TypeSpec("integer"), type=TEXT, level=TEXT, title=TEXT, body=TEXT,
    targetRoute=TEXT, targetId=TEXT, createdAt=TypeSpec("datetime"), unread=BOOLEAN,
    transferId=TypeSpec("integer", nullable=True))


def result(data):
    return OperationResult(ResultState.COMPLETED, data)


def listing(context, values):
    return result(service.notifications(context.tenant))


def read(context, values):
    return result(service.read_notifications(context.tenant, values))


def bindings(context, values):
    return result(service.bindings(context.tenant))


def issue_code(context, values):
    return result(service.create_binding_code(context.tenant, values["integration_id"]))


def update_binding(context, values):
    return result(service.update_binding(context.tenant, values["integration_id"], values["pushTypes"]))


def delete_binding(context, values):
    return result(service.delete_binding(context.tenant, values["integration_id"]))


def preference(context, values):
    return result(service.notification_preference(context.tenant, values["transport"]))


def update_preference(context, values):
    return result(service.notification_preference(context.tenant, values["transport"],
        {key: values[key] for key in ("enabled", "types") if key in values}))


for key, title, inputs, outputs, handler, method, suffix, view in (
    ("notifications.get", "native.notifications_list", obj(),
        obj(items=TypeSpec("array", items=NOTIFICATION), unreadCount=TypeSpec("integer")),
        listing, "GET", "", "NotificationListView"),
    ("notifications.read.post", "native.notifications_read", obj(all=BOOLEAN,
        conversationId=TypeSpec("integer"), ids=TypeSpec("array", items=TypeSpec("integer"))),
        obj(unreadCount=TypeSpec("integer")), read, "POST", "read/", "NotificationReadView"),
    ("notifications.bindings.get", "native.notification_bindings", obj(), obj(items=TypeSpec("array",
        items=obj(integrationId=TypeSpec("integer"), provider=TEXT, name=TEXT, botUsername=TEXT,
            bound=BOOLEAN, pushTypes=STRINGS)), availableTypes=AVAILABLE),
        bindings, "GET", "messenger-bindings/", "MessengerBindingListView"),
    ("notifications.binding.post", "native.notification_binding_code", obj(integration_id=IDENTIFIER),
        obj(code=TypeSpec("string", secret=True), deepLink=TypeSpec("string", secret=True),
            expiresAt=TypeSpec("datetime")), issue_code, "POST",
        "messenger-bindings/<int:integration_id>/", "MessengerBindingDetailView"),
    ("notifications.binding.patch", "native.notification_binding_update",
        obj(integration_id=IDENTIFIER, pushTypes=required(STRINGS)), obj(pushTypes=STRINGS),
        update_binding, "PATCH", "messenger-bindings/<int:integration_id>/", "MessengerBindingDetailView"),
    ("notifications.binding.delete", "native.notification_binding_delete", obj(integration_id=IDENTIFIER),
        obj(ok=BOOLEAN), delete_binding, "DELETE", "messenger-bindings/<int:integration_id>/", "MessengerBindingDetailView"),
    ("notifications.preference.get", "native.notification_preference", obj(transport=required(TRANSPORT)),
        PREFERENCE, preference, "GET", "preferences/<str:transport>/", "NotificationPreferenceView"),
    ("notifications.preference.patch", "native.notification_preference_update",
        obj(transport=required(TRANSPORT), enabled=BOOLEAN, types=STRINGS), PREFERENCE,
        update_preference, "PATCH", "preferences/<str:transport>/", "NotificationPreferenceView"),
):
    action(key=key, title=title, input=inputs, output=outputs, handler=handler,
        capability="", scope="organization", route=f"notifications/{suffix}",
        view=f"chatballs.notifications.views.{view}", method=method)
