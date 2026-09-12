"""Доступ к настройкам установки: адрес, почта, TURN, хранилище файлов.

Это свойства инсталляции, а не организации, поэтому право их менять не
выводится из роли в организации: владелец одной организации не должен
переключать SMTP или бакет, общие для всех. Менять их может только
администратор установки — глобальный признак на учётной записи
(``HumanUser.is_instance_admin``). Первым его получает владелец из мастера
первого запуска; дальше признак передают командой ``set_instance_admin``.

Читать настройки без секретов может тот, кто видит «Настройки» хотя бы в одной
организации: карточка relay для звонков показывает адреса TURN администратору
организации, менять их он не может.
"""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.policy import has_capability_any_scope
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user

INSTANCE_SETTINGS_VIEW_CAPABILITY = "settings.view"


def is_instance_admin(user: object) -> bool:
    return (
        isinstance(user, HumanUser)
        and user.is_active
        and bool(getattr(user, "is_instance_admin", False))
    )


def can_view_instance_settings(user: object) -> bool:
    """Администратор установки или менеджер хотя бы одной организации.

    Членства — тенантные строки: каждое читается в контексте своей организации,
    как при сборке сессии.
    """

    if is_instance_admin(user):
        return True
    if not isinstance(user, HumanUser) or not user.is_active:
        return False
    for route in membership_routes_for_user(user.id):
        with tenant_atomic(route.organization_id):
            membership = (
                OrganizationMembership.objects.select_related("user")
                .filter(id=route.resource_id, user=user, blocked_at__isnull=True)
                .first()
            )
        if membership is not None and has_capability_any_scope(
            membership, INSTANCE_SETTINGS_VIEW_CAPABILITY
        ):
            return True
    return False


class InstanceSettingsPermission(BasePermission):
    """GET — менеджеру любой организации, изменения — администратору установки."""

    message = "Instance administrator rights are required"

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return can_view_instance_settings(request.user)
        return is_instance_admin(request.user)


class IsInstanceAdmin(BasePermission):
    message = "Instance administrator rights are required"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_instance_admin(request.user)
