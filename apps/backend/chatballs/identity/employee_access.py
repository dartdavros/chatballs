"""Employee access changes within the existing management transaction."""

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.employee_validation import resolve_groups
from chatballs.identity.group_models import EmployeeGroupMember
from chatballs.identity.models import EmployeeRole
from chatballs.identity.supervision_models import EmployeeGroupSupervision


def set_groups(profile, groups) -> None:
    profile.group_links.all().delete()
    EmployeeGroupMember.objects.bulk_create([
        EmployeeGroupMember(
            organization_id=profile.organization_id, group=group, employee=profile
        )
        for group in groups
    ])
    getattr(profile, "_prefetched_objects_cache", {}).pop("group_links", None)


def resolve_supervised_groups(profile, role, body):
    if "supervisedGroupIds" in body:
        raw = body["supervisedGroupIds"]
        if not isinstance(raw, list) or any(type(item) is not int for item in raw):
            return None, t("admin.supervised_group_ids_invalid")
        groups, error = resolve_groups(profile.organization, raw)
        if error:
            return None, error
        if groups and role != EmployeeRole.SUPERVISOR:
            return None, t("admin.supervised_groups_require_supervisor")
        return groups, None
    # No stale control area survives removal of the supervisor role.
    if role != EmployeeRole.SUPERVISOR:
        return [], None
    return None, None


def update_employee_access(request, profile, role, groups, *, actor=None) -> None:
    old_role = profile.role
    old_ids = sorted(profile.supervision_links.values_list("group_id", flat=True))
    new_ids = old_ids if groups is None else sorted(group.id for group in groups)
    profile.role = role
    if old_role != role:
        profile.save(update_fields=["role"])
    if old_ids != new_ids:
        profile.supervision_links.all().delete()
        EmployeeGroupSupervision.objects.bulk_create([
            EmployeeGroupSupervision(
                organization_id=profile.organization_id, employee=profile, group=group
            )
            for group in groups
        ])
        getattr(profile, "_prefetched_objects_cache", {}).pop("supervision_links", None)
    changes = []
    if old_role != role:
        changes.append(("identity.employee_role_changed", {"oldRole": old_role, "role": role}))
    if old_ids != new_ids:
        changes.append(("identity.employee_supervised_groups_changed", {
            "oldGroupIds": old_ids, "groupIds": new_ids,
        }))
    for action, payload in changes:
        record_audit_event(
            action=action, actor=actor if actor is not None else request.user, organization=profile.organization,
            object_type="HumanUser", object_id=str(profile.user_id),
            payload=payload, request=request,
        )
