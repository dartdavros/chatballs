"""WEB adapter: durable availability through the authenticated session poll."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.ratings.credentials import credential_for, hash_credential
from chatballs.ratings.models import RatingRequest, RatingSettings
from chatballs.ratings.presentation import request_presentation
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.models import WebSession


def available_sessions():
    return WebSession.objects.filter(
        connection__provider="WEB", connection__is_active=True, connection__status="OK",
        connection__channel__is_active=True, widget__status="PUBLISHED",
        last_seen_at__gt=timezone.now() - timedelta(seconds=settings.CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS),
    )


def deliver_due_requests(context):
    with tenant_atomic(context):
        policy = RatingSettings.objects.select_for_update().filter(
            organization_id=context.organization_id,
        ).first()
        pending = RatingRequest.objects.select_for_update().filter(
            organization_id=context.organization_id, sent_at__isnull=True,
            cancelled_at__isnull=True, due_at__lte=timezone.now(),
        ).order_by("due_at", "pk")[:100]
        delivered = 0
        for request in pending:
            session = available_sessions().filter(
                pk=request.delivery_session_id, organization_id=context.organization_id,
                widget__integration_id=request.conversation.connection_id,
                identity__contact_id=request.conversation.contact_id,
            ).first()
            if policy is None or not policy.enabled or session is None or request.completion.transport != "WEB":
                request.cancelled_at = timezone.now()
                request.save(update_fields=["cancelled_at"])
                continue
            request.sent_at = timezone.now()
            request.credential_hash = hash_credential(credential_for(request))
            request.save(update_fields=["sent_at", "credential_hash"])
            delivered += 1
        return delivered


def session_requests(session):
    if not available_sessions().filter(pk=session.pk, organization_id=session.organization_id).exists():
        return []
    requests = RatingRequest.objects.filter(
        organization_id=session.organization_id, delivery_session_id=session.pk,
        completion__transport="WEB",
        sent_at__isnull=False, cancelled_at__isnull=True,
        result__isnull=True,
    ).order_by("due_at", "pk")
    return [
        {"credential": credential_for(request), "text": request.text,
         "scale": request.scale, "expiresAt": None,
         "presentation": request_presentation(request)}
        for request in requests
        if hash_credential(credential_for(request)) == request.credential_hash
    ]
