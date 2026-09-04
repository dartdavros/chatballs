from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.group_models import EmployeeGroup, EmployeeGroupMember
from hub_platform.identity.models import OrganizationMembership

# Группы сотрудников (ADR-HUB-0043): имя + состав, только граница видимости
# диалогов. Управляют OWNER/ADMIN; сотрудник видит свои группы в session payload.


def _group_payload(group: EmployeeGroup, member_count: int | None = None) -> dict[str, object]:
    if member_count is None:
        member_count = group.member_links.count()
    return {
        "id": group.id,
        "name": group.name,
        "memberCount": member_count,
        "memberIds": sorted(
            group.member_links.values_list("employee__user_id", flat=True)
        ),
        "createdAt": group.created_at.isoformat(),
    }


def _resolve_members(organization, raw) -> tuple[list[OrganizationMembership] | None, str | None]:
    if raw is None:
        return None, None
    if not isinstance(raw, list) or any(not isinstance(item, int) for item in raw):
        return None, "memberIds must be a list of user ids"
    requested = list(dict.fromkeys(raw))
    members = list(
        OrganizationMembership.objects.filter(
            organization=organization, user_id__in=requested
        )
    )
    if len(members) != len(requested):
        return None, "Employee not found"
    return members, None


class GroupListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "employees.view", "POST": "groups.manage"}

    def get(self, request: Request) -> Response:
        groups = (
            EmployeeGroup.objects.filter(organization=request.tenant_context.organization)
            .annotate(member_count=Count("member_links"))
            .order_by("name")
        )
        return Response(
            {"items": [_group_payload(group, group.member_count) for group in groups]}
        )

    @transaction.atomic
    def post(self, request: Request) -> Response:
        organization = request.tenant_context.organization
        name = str(request.data.get("name", "")).strip()
        members, members_error = _resolve_members(organization, request.data.get("memberIds"))
        if members_error:
            return Response({"detail": members_error}, status=400)
        try:
            group = EmployeeGroup.objects.create(organization=organization, name=name)
        except (ValidationError, IntegrityError):
            return Response({"detail": "Группа с таким именем уже есть"}, status=400)
        if members:
            EmployeeGroupMember.objects.bulk_create(
                [
                    EmployeeGroupMember(
                        organization=organization, group=group, employee=member
                    )
                    for member in members
                ]
            )
        record_audit_event(
            action="identity.group_created",
            actor=request.user,
            organization=organization,
            object_type="EmployeeGroup",
            object_id=str(group.id),
            payload={"name": group.name},
            request=request,
        )
        return Response({"group": _group_payload(group)}, status=201)


class GroupDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"PATCH": "groups.manage", "DELETE": "groups.manage"}

    def _group(self, request: Request, group_id: int) -> EmployeeGroup | None:
        return EmployeeGroup.objects.filter(
            organization=request.tenant_context.organization, id=group_id
        ).first()

    @transaction.atomic
    def patch(self, request: Request, group_id: int) -> Response:
        group = self._group(request, group_id)
        if group is None:
            return Response({"detail": "Group not found"}, status=404)
        if "name" in request.data:
            group.name = str(request.data.get("name", "")).strip()
            try:
                group.save()
            except (ValidationError, IntegrityError):
                return Response({"detail": "Группа с таким именем уже есть"}, status=400)
        members, members_error = _resolve_members(
            group.organization, request.data.get("memberIds")
        )
        if members_error:
            return Response({"detail": members_error}, status=400)
        if members is not None:
            group.member_links.all().delete()
            EmployeeGroupMember.objects.bulk_create(
                [
                    EmployeeGroupMember(
                        organization=group.organization, group=group, employee=member
                    )
                    for member in members
                ]
            )
        record_audit_event(
            action="identity.group_updated",
            actor=request.user,
            organization=group.organization,
            object_type="EmployeeGroup",
            object_id=str(group.id),
            request=request,
        )
        return Response({"group": _group_payload(group)})

    @transaction.atomic
    def delete(self, request: Request, group_id: int) -> Response:
        group = self._group(request, group_id)
        if group is None:
            return Response({"detail": "Group not found"}, status=404)
        # SET_NULL на каналах и диалогах: их диалоги становятся общими.
        group_payload = _group_payload(group)
        group.delete()
        record_audit_event(
            action="identity.group_deleted",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="EmployeeGroup",
            object_id=str(group_id),
            payload={"name": group_payload["name"]},
            request=request,
        )
        return Response({"deleted": True})
