"""Group management shared by HTTP and native scenario actions."""

import re

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_access import update_employee_access
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import ResourceScope, authorize


def _require(context, capability):
    if not authorize(context.membership, capability, ResourceScope(context.organization_id)):
        raise PermissionDenied()


def group_payload(group, member_count=None):
    return {
        "id": group.id, "name": group.name, "color": group.color,
        "memberCount": group.member_links.count() if member_count is None else member_count,
        "memberIds": sorted(group.member_links.values_list("employee__user_id", flat=True)),
        "createdAt": group.created_at.isoformat(),
    }


def list_groups(context):
    _require(context, "employees.view")
    rows = EmployeeGroup.objects.filter(organization_id=context.organization_id).annotate(
        member_count=Count("member_links")).order_by("name")
    return {"items": [group_payload(row, row.member_count) for row in rows]}


def _members(context, data):
    raw = data.get("memberIds")
    if raw is None:
        return None
    if not isinstance(raw, list) or any(type(item) is not int for item in raw):
        raise ValidationError({"detail": t("admin.group_members_invalid")})
    members = list(OrganizationMembership.objects.filter(
        organization_id=context.organization_id, user_id__in=set(raw)))
    if len(members) != len(set(raw)):
        raise ValidationError({"detail": t("admin.employee_not_found")})
    return members


def _color(value):
    text = str(value or "").strip()
    if text and not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise ValidationError({"detail": t("conversations.invalid_colour")})
    return text.lower()


def _set_members(group, members):
    if members is not None:
        group.member_links.all().delete()
        EmployeeGroupMember.objects.bulk_create([
            EmployeeGroupMember(organization_id=group.organization_id, group=group, employee=member)
            for member in members
        ])


def _audit(context, action, group_id, request, payload=None):
    record_audit_event(action=action, actor=context.membership.user,
        organization=context.organization, object_type="EmployeeGroup",
        object_id=str(group_id), payload=payload, request=request)


def _group(context, group_id):
    _require(context, "groups.manage")
    group = EmployeeGroup.objects.select_for_update().filter(
        organization_id=context.organization_id, pk=group_id).first()
    if group is None:
        raise NotFound(t("admin.group_not_found"))
    return group


@transaction.atomic
def create_group(context, data, *, request=None):
    _require(context, "groups.manage")
    members = _members(context, data)
    color = _color(data.get("color"))
    try:
        with transaction.atomic():
            group = EmployeeGroup.objects.create(organization_id=context.organization_id,
                name=str(data.get("name", "")).strip(), color=color)
    except (ModelValidationError, IntegrityError):
        raise ValidationError({"detail": t("admin.group_name_taken")}) from None
    _set_members(group, members)
    _audit(context, "identity.group_created", group.id, request, {"name": group.name})
    return {"group": group_payload(group)}


@transaction.atomic
def update_group(context, group_id, data, *, request=None):
    group = _group(context, group_id)
    members = _members(context, data)
    if "color" in data:
        group.color = _color(data["color"])
    if "name" in data:
        group.name = str(data["name"]).strip()
    if "name" in data or "color" in data:
        try:
            with transaction.atomic():
                group.save()
        except (ModelValidationError, IntegrityError):
            raise ValidationError({"detail": t("admin.group_name_taken")}) from None
    _set_members(group, members)
    _audit(context, "identity.group_updated", group.id, request)
    return {"group": group_payload(group)}


@transaction.atomic
def delete_group(context, group_id, *, request=None):
    group = _group(context, group_id)
    name = group.name
    supervisors = OrganizationMembership.objects.filter(
        organization_id=context.organization_id, supervision_links__group=group,
    ).select_for_update(of=("self",)).order_by("id")
    for supervisor in supervisors:
        remaining = [link.group for link in supervisor.supervision_links.select_related("group")
            if link.group_id != group.id]
        update_employee_access(request, supervisor, supervisor.role, remaining,
            actor=context.membership.user)
    group.delete()
    _audit(context, "identity.group_deleted", group_id, request, {"name": name})
    return {"deleted": True}
