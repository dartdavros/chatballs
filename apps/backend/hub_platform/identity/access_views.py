from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.access_services import create_access_assignment
from hub_platform.identity.capabilities import CAPABILITY_REGISTRY, capability_spec
from hub_platform.identity.governance import EmployeeAction, can_manage_employee
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    EmployeeAccessAssignment,
    EmployeeProfile,
)
from hub_platform.identity.policy import can_administer_access
from hub_platform.identity.sessions import revoke_user_sessions


def _profile_payload(profile: AccessProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "isSystem": profile.is_system,
        "isActive": profile.is_active,
        "capabilities": sorted(
            profile.capability_links.values_list("capability_code", flat=True)
        ),
    }


def assignment_payload(assignment: EmployeeAccessAssignment) -> dict[str, object]:
    return {
        "id": assignment.id,
        "profile": _profile_payload(assignment.access_profile),
        "scopeType": assignment.scope_type,
        "departmentId": assignment.department_id,
        "departmentCode": assignment.department.code if assignment.department_id else None,
        "revokedAt": assignment.revoked_at.isoformat() if assignment.revoked_at else None,
    }


def _manager_required(request: Request) -> Response | None:
    if can_administer_access(request.user):
        return None
    return Response({"detail": "Employee access management is not allowed"}, status=403)


def _capability_codes(raw: object) -> tuple[list[str], str | None]:
    if not isinstance(raw, list) or any(not isinstance(code, str) for code in raw):
        return [], "capabilities must be a list of registry codes"
    codes = list(dict.fromkeys(raw))
    try:
        for code in codes:
            spec = capability_spec(code)
            if not spec.assignable or spec.protected:
                return [], f"Capability cannot be assigned: {code}"
    except ValueError as error:
        return [], str(error)
    return codes, None


class CapabilityRegistryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        return Response(
            {
                "items": [
                    {
                        "code": spec.code,
                        "name": spec.name,
                        "description": spec.description,
                        "allowedScopes": sorted(spec.allowed_scopes),
                    }
                    for spec in CAPABILITY_REGISTRY.values()
                    if spec.assignable and not spec.protected
                ]
            }
        )


class AccessProfileListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        profiles = AccessProfile.objects.filter(
            organization=request.user.employee_profile.organization
        ).prefetch_related("capability_links")
        return Response({"items": [_profile_payload(profile) for profile in profiles.order_by("name")]})

    @transaction.atomic
    def post(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        codes, error = _capability_codes(request.data.get("capabilities", []))
        if error:
            return Response({"detail": error}, status=400)
        actor = request.user.employee_profile
        try:
            profile = AccessProfile.objects.create(
                organization=actor.organization,
                name=str(request.data.get("name", "")),
                description=str(request.data.get("description", "")),
            )
            AccessProfileCapability.objects.bulk_create(
                [
                    AccessProfileCapability(access_profile=profile, capability_code=code)
                    for code in codes
                ]
            )
        except (ValidationError, IntegrityError) as exc:
            return Response({"detail": str(exc)}, status=400)
        record_audit_event(
            action="access_profile.created",
            actor=request.user,
            organization=actor.organization,
            object_type="AccessProfile",
            object_id=str(profile.id),
            payload={"capabilities": codes},
            request=request,
        )
        return Response({"profile": _profile_payload(profile)}, status=201)


class AccessProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _profile(self, request: Request, profile_id: int) -> AccessProfile | None:
        return (
            AccessProfile.objects.filter(
                id=profile_id, organization=request.user.employee_profile.organization
            )
            .prefetch_related("capability_links")
            .first()
        )

    @transaction.atomic
    def patch(self, request: Request, profile_id: int) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        profile = self._profile(request, profile_id)
        if profile is None:
            return Response({"detail": "Access profile not found"}, status=404)
        codes, error = _capability_codes(
            request.data.get(
                "capabilities",
                list(profile.capability_links.values_list("capability_code", flat=True)),
            )
        )
        if error:
            return Response({"detail": error}, status=400)
        affected_user_ids = list(
            profile.assignments.filter(revoked_at__isnull=True).values_list(
                "employee__user_id", flat=True
            )
        )
        profile.name = str(request.data.get("name", profile.name))
        profile.description = str(request.data.get("description", profile.description))
        profile.is_active = bool(request.data.get("isActive", profile.is_active))
        try:
            profile.save()
            profile.capability_links.all().delete()
            AccessProfileCapability.objects.bulk_create(
                [
                    AccessProfileCapability(access_profile=profile, capability_code=code)
                    for code in codes
                ]
            )
        except (ValidationError, IntegrityError) as exc:
            return Response({"detail": str(exc)}, status=400)
        record_audit_event(
            action="access_profile.updated" if profile.is_active else "access_profile.disabled",
            actor=request.user,
            organization=profile.organization,
            object_type="AccessProfile",
            object_id=str(profile.id),
            payload={"capabilities": codes},
            request=request,
        )
        for user_id in affected_user_ids:
            revoke_user_sessions(user_id)
        return Response({"profile": _profile_payload(profile)})

    def delete(self, request: Request, profile_id: int) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        profile = self._profile(request, profile_id)
        if profile is None:
            return Response({"detail": "Access profile not found"}, status=404)
        if profile.is_system or profile.assignments.exists():
            return Response({"detail": "Profile must be disabled to preserve access history"}, status=409)
        profile.delete()
        return Response(status=204)


class EmployeeAccessAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.user.employee_profile
        target = EmployeeProfile.objects.filter(
            user_id=user_id, organization=actor.organization
        ).first()
        if target is None:
            return Response({"detail": "Employee not found"}, status=404)
        if not can_manage_employee(actor, target, EmployeeAction.CHANGE_ACCESS):
            return Response({"detail": "Access assignment is not allowed"}, status=403)
        try:
            assignment = create_access_assignment(
                actor=actor, employee=target, payload=request.data
            )
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        except IntegrityError as exc:
            return Response({"detail": str(exc)}, status=409)
        record_audit_event(
            action="access_assignment.created",
            actor=request.user,
            organization=actor.organization,
            object_type="EmployeeAccessAssignment",
            object_id=str(assignment.id),
            payload={"employeeId": target.user_id, "scopeType": assignment.scope_type},
            request=request,
        )
        revoke_user_sessions(target.user_id)
        return Response({"assignment": assignment_payload(assignment)}, status=201)


class EmployeeAccessAssignmentRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, user_id: int, assignment_id: int) -> Response:
        actor = request.user.employee_profile
        assignment = EmployeeAccessAssignment.objects.select_related(
            "employee", "access_profile", "department"
        ).filter(
            id=assignment_id,
            employee__user_id=user_id,
            employee__organization=actor.organization,
            revoked_at__isnull=True,
        ).first()
        if assignment is None:
            return Response({"detail": "Access assignment not found"}, status=404)
        if not can_manage_employee(actor, assignment.employee, EmployeeAction.CHANGE_ACCESS):
            return Response({"detail": "Access assignment is not allowed"}, status=403)
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])
        record_audit_event(
            action="access_assignment.revoked",
            actor=request.user,
            organization=actor.organization,
            object_type="EmployeeAccessAssignment",
            object_id=str(assignment.id),
            request=request,
        )
        revoke_user_sessions(assignment.employee.user_id)
        return Response({"assignment": assignment_payload(assignment)})
