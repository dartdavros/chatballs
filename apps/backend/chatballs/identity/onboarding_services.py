"""Organization onboarding facts and per-member checklist state."""

from datetime import datetime

from django.utils import timezone as django_timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.i18n import t
from chatballs.identity.policy import has_capability_any_scope


def onboarding_status(context):
    if not has_capability_any_scope(context.membership, "settings.view"):
        raise PermissionDenied()
    membership = context.membership
    return {"operationMode": context.organization.operation_mode,
        "steps": onboarding_steps(context.organization_id),
        "dismissedAt": _isoformat(membership.onboarding_dismissed_at if membership else None),
        "completedAt": _isoformat(membership.onboarding_completed_at if membership else None)}


def change_onboarding(context, body):
    membership = context.membership
    if membership is None:
        raise PermissionDenied(t("onboarding.membership_required"))
    if not has_capability_any_scope(membership, "settings.view"):
        raise PermissionDenied()
    action = str(body.get("action") or "dismiss")
    now = django_timezone.now()
    if action == "dismiss":
        membership.onboarding_dismissed_at = now
    elif action == "complete":
        membership.onboarding_dismissed_at = now
        membership.onboarding_completed_at = now
    elif action == "restart":
        membership.onboarding_dismissed_at = None
        membership.onboarding_completed_at = None
    else:
        raise ValidationError({"detail": t("onboarding.unknown_action")})
    membership.save(update_fields=["onboarding_dismissed_at", "onboarding_completed_at"])
    return onboarding_status(context)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def onboarding_steps(organization_id: int) -> dict[str, bool]:
    """Восемь фактов настройки установки, каждый — один запрос на существование."""

    from chatballs.ai.models import AIAgent, AIAgentStatus, Knowledge
    from chatballs.conversations.models import Conversation
    from chatballs.identity import instance_settings
    from chatballs.identity.models import Organization, OrganizationMembership
    from chatballs.integrations.models import Integration, IntegrationKind
    from chatballs.webchat.models import WebChatWidget, WebChatWidgetStatus

    organization = Organization.objects.filter(pk=organization_id).first()
    return {
        "providerConnected": Integration.objects.filter(
            organization_id=organization_id,
            kind=IntegrationKind.LLM_PROVIDER,
        ).exists(),
        "agentActive": AIAgent.objects.filter(
            organization_id=organization_id,
            status=AIAgentStatus.ACTIVE,
        ).exists(),
        "knowledgeFilled": Knowledge.objects.filter(organization_id=organization_id).exists(),
        "connectionBound": Integration.objects.filter(
            organization_id=organization_id,
            kind=IntegrationKind.MESSENGER,
            channel__isnull=False,
        ).exists(),
        "widgetPublished": WebChatWidget.objects.filter(
            organization_id=organization_id,
            status=WebChatWidgetStatus.PUBLISHED,
        ).exists(),
        "employeeInvited": (
            OrganizationMembership.objects.filter(organization_id=organization_id).count() > 1
            or (organization is not None and organization.invitations.exists())
        ),
        # Шаг про саму установку, а не про организацию: домен и исходящая почта
        # общие для всех организаций на сервере.
        "platformConfigured": bool(instance_settings.public_host()) and instance_settings.email_is_configured(),
        "firstConversation": Conversation.objects.filter(organization_id=organization_id).exists(),
    }
