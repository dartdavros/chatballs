"""Personal notification operations shared by HTTP and scenario actions."""

from rest_framework.exceptions import NotFound, ValidationError

from chatballs.i18n import t
from chatballs.notifications.binding import deep_link, issue_binding_code, notifier_integrations
from chatballs.notifications.models import MessengerBinding, NotificationRead, NotificationTransport
from chatballs.notifications.preferences import preference_for, preference_types, update_preference
from chatballs.notifications.selectors import unread_for, visible_for
from chatballs.notifications.serializers import notification_payload
from chatballs.notifications.services import TYPE_META, mark_read


def available_types():
    return [{"code": code, "label": t(meta["label"])} for code, meta in TYPE_META.items()]


def notifications(context):
    items = list(visible_for(context)[:50])
    read_ids = set(NotificationRead.objects.filter(user=context.actor_user,
        notification__in=items).values_list("notification_id", flat=True))
    return {"items": [notification_payload(row, unread=row.id not in read_ids) for row in items],
        "unreadCount": unread_for(context).count()}


def read_notifications(context, values):
    conversation_id = values.get("conversationId")
    if values.get("all"):
        mark_read(context=context, all_unread=True)
    elif conversation_id is not None:
        if not isinstance(conversation_id, int) or isinstance(conversation_id, bool):
            raise ValidationError({"detail": t("notifications.conversation_id_number")})
        mark_read(context=context, conversation_id=conversation_id)
    else:
        ids = values.get("ids")
        if not isinstance(ids, list):
            raise ValidationError({"detail": t("notifications.ids_list_or_all")})
        mark_read(context=context, ids=[i for i in ids if isinstance(i, int)])
    return {"unreadCount": unread_for(context).count()}


def bindings(context):
    by_integration = {row.integration_id: row for row in MessengerBinding.objects.filter(
        user=context.actor_user, integration__organization=context.organization)}
    types = preference_types(organization_id=context.organization_id,
        user_id=context.actor_user.pk, transport=NotificationTransport.MESSENGER)
    return {"items": [{"integrationId": row.pk, "provider": row.provider, "name": row.name,
        "botUsername": row.config.get("bot_username", ""), "bound": row.pk in by_integration,
        "pushTypes": types if row.pk in by_integration else []}
        for row in notifier_integrations(context)], "availableTypes": available_types()}


def create_binding_code(context, integration_id):
    integration = notifier_integrations(context).filter(pk=integration_id).first()
    if integration is None:
        raise NotFound({"detail": t("profile.notification_bot_not_found")})
    code = issue_binding_code(context=context, integration=integration)
    return {"code": code.code, "deepLink": deep_link(integration, code.code),
        "expiresAt": code.expires_at.isoformat()}


def update_binding(context, integration_id, types):
    if not MessengerBinding.objects.filter(user=context.actor_user, integration_id=integration_id,
            integration__organization=context.organization).exists():
        raise NotFound({"detail": t("profile.link_not_found")})
    if not isinstance(types, list):
        raise ValidationError({"detail": t("notifications.push_types_list")})
    preference = update_preference(organization_id=context.organization_id,
        user_id=context.actor_user.pk, transport=NotificationTransport.MESSENGER, types=types)
    return {"pushTypes": preference.types}


def delete_binding(context, integration_id):
    MessengerBinding.objects.filter(user=context.actor_user, integration_id=integration_id,
        integration__organization=context.organization).delete()
    update_preference(organization_id=context.organization_id, user_id=context.actor_user.pk,
        transport=NotificationTransport.MESSENGER, enabled=False)
    return {"ok": True}


def preference_payload(preference):
    return {"transport": preference.transport, "enabled": preference.enabled,
        "types": list(preference.types or []), "availableTypes": available_types()}


def notification_preference(context, transport, changes=None):
    if transport not in NotificationTransport.values:
        raise NotFound({"detail": t("notifications.unknown_transport")})
    arguments = dict(organization_id=context.organization_id,
        user_id=context.actor_user.pk, transport=transport)
    if changes is None:
        return preference_payload(preference_for(**arguments))
    types, enabled = changes.get("types"), changes.get("enabled")
    if types is not None and not isinstance(types, list):
        raise ValidationError({"detail": t("notifications.push_types_list")})
    if enabled is not None and not isinstance(enabled, bool):
        raise ValidationError({"detail": t("notifications.enabled_bool")})
    return preference_payload(update_preference(**arguments, types=types, enabled=enabled))
