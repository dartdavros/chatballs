from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.access_payloads import (
    assignment_payload,
    capability_codes,
    capability_registry_payload,
    profile_payload,
)
from hub_platform.identity.access_services import allowed_profile_scopes, create_access_assignment
from hub_platform.identity.governance import EmployeeAction, can_manage_employee
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    EmployeeAccessAssignment,
    OrganizationMembership,
)
from hub_platform.identity.policy import can_administer_access


def _manager_required(request: Request) -> Response | None:
    if can_administer_access(request.tenant_context.membership):
        return None
    return Response({"detail": "Employee access management is not allowed"}, status=403)


class CapabilityRegistryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        return Response({"items": capability_registry_payload()})


class AccessProfileListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        profiles = AccessProfile.objects.filter(
            organization=request.tenant_context.organization
        ).prefetch_related("capability_links").annotate(
            active_assignment_count=Count(
                "assignments",
                filter=Q(assignments__revoked_at__isnull=True),
                distinct=True,
            )
        )
        return Response({"items": [profile_payload(profile) for profile in profiles.order_by("name")]})

    @transaction.atomic
    def post(self, request: Request) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        codes, error = capability_codes(request.data.get("capabilities", []))
        if error:
            return Response({"detail": error}, status=400)
        actor = request.tenant_context.membership
        name = str(request.data.get("name", "")).strip()
        if not name:
            return Response({"detail": "Access profile name is required"}, status=400)
        try:
            profile = AccessProfile.objects.create(
                organization=actor.organization,
                name=name,
                description=str(request.data.get("description", "")).strip(),
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
        return Response({"profile": profile_payload(profile)}, status=201)


class AccessProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _profile(self, request: Request, profile_id: int) -> AccessProfile | None:
        return (
            AccessProfile.objects.filter(
                id=profile_id, organization=request.tenant_context.organization
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
        if profile.is_system:
            return Response({"detail": "System access profile is read-only"}, status=409)
        codes, error = capability_codes(
            request.data.get(
                "capabilities",
                list(profile.capability_links.values_list("capability_code", flat=True)),
            )
        )
        if error:
            return Response({"detail": error}, status=400)
        requested_scopes = set(
            profile.assignments.filter(revoked_at__isnull=True).values_list(
                "scope_type", flat=True
            )
        )
        if not requested_scopes.issubset(allowed_profile_scopes(codes)):
            return Response(
                {"detail": "Profile capabilities conflict with active assignment scopes"},
                status=409,
            )
        profile.name = str(request.data.get("name", profile.name)).strip()
        if not profile.name:
            return Response({"detail": "Access profile name is required"}, status=400)
        profile.description = str(request.data.get("description", profile.description)).strip()
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
        return Response({"profile": profile_payload(profile)})

    def delete(self, request: Request, profile_id: int) -> Response:
        if (denied := _manager_required(request)) is not None:
            return denied
        profile = self._profile(request, profile_id)
        if profile is None:
            return Response({"detail": "Access profile not found"}, status=404)
        if profile.is_system or profile.assignments.exists():
            return Response({"detail": "Profile must be disabled to preserve access history"}, status=409)
        record_audit_event(
            action="access_profile.deleted",
            actor=request.user,
            organization=profile.organization,
            object_type="AccessProfile",
            object_id=str(profile.id),
            request=request,
        )
        profile.delete()
        return Response(status=204)


class EmployeeAccessAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, user_id: int) -> Response:
        actor = request.tenant_context.membership
        target = OrganizationMembership.objects.filter(
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
        return Response({"assignment": assignment_payload(assignment)}, status=201)


class EmployeeAccessAssignmentRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, user_id: int, assignment_id: int) -> Response:
        actor = request.tenant_context.membership
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
        return Response({"assignment": assignment_payload(assignment)})
