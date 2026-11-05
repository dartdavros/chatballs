"""Organization label catalog shared by HTTP and scenario actions."""

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chatballs.conversations.models import ConversationLabel
from chatballs.i18n import t
from chatballs.identity.policy import has_capability_any_scope


def _require(context, capability):
    if not has_capability_any_scope(context.membership, capability):
        raise PermissionDenied()


def label_payload(label):
    return {"id": label.pk, "name": label.name, "color": label.color}


def labels_for(context):
    _require(context, "conversations.view")
    return ConversationLabel.objects.filter(organization_id=context.organization_id)


def _fields(data):
    fields = {}
    if "name" in data:
        name = str(data["name"]).strip()
        if not name or len(name) > 60:
            raise ValidationError({"detail": t("conversations.label_name_length")})
        fields["name"] = name
    if "color" in data:
        color = str(data["color"]).strip()
        if len(color) > 20:
            raise ValidationError({"detail": t("conversations.invalid_colour")})
        fields["color"] = color
    return fields


@transaction.atomic
def create_label(*, context, name, color=""):
    _require(context, "conversations.operate")
    fields = _fields({"name": name, "color": color})
    existing = ConversationLabel.objects.filter(organization_id=context.organization_id,
        name__iexact=fields["name"]).first()
    if existing is not None:
        return existing, False
    return ConversationLabel.objects.create(organization_id=context.organization_id, **fields), True


def _label(context, label_id):
    _require(context, "settings.manage")
    try:
        return ConversationLabel.objects.get(organization_id=context.organization_id, pk=label_id)
    except ConversationLabel.DoesNotExist:
        raise NotFound(t("conversations.label_not_found")) from None


@transaction.atomic
def update_label(*, context, label_id, changes):
    label = _label(context, label_id)
    for name, value in _fields(changes).items():
        setattr(label, name, value)
    label.save()
    return label


@transaction.atomic
def delete_label(*, context, label_id):
    _label(context, label_id).delete()
