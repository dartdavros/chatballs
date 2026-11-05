"""Credential-scoped question/read and atomic immutable submission."""

from contextlib import contextmanager

from django.db import connection
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.ratings.credentials import hash_credential
from chatballs.ratings.models import CustomerRating, RatingRequest
from chatballs.ratings.presentation import request_presentation
from chatballs.ratings.validation import COMMENT_LIMIT, validate_response
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import load_organization


class RatingConflict(APIException):
    status_code = 409
    default_code = "rating_conflict"


def result_payload(result):
    return {"value": int(result.value), "comment": result.comment,
            "receivedAt": result.received_at.isoformat()}


def question_payload(request):
    result = CustomerRating.objects.filter(request=request).first()
    return {"text": request.text, "scale": request.scale,
            "expiresAt": (request.expires_at.isoformat()
                          if request.completion.transport != "WEB" and request.expires_at else None),
            "commentMaxLength": COMMENT_LIMIT,
            "result": result_payload(result) if result else None,
            "presentation": request_presentation(request)}


@contextmanager
def resolved_request(token, *, expected_organization_id=None):
    digest = hash_credential(token) if token else ""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT organization_id, resource_id FROM chatballs.rating_request_directory "
            "WHERE lookup_key = %s LIMIT 1", [digest],
        )
        route = cursor.fetchone()
    if route and expected_organization_id is not None and route[0] != expected_organization_id:
        raise NotFound(t("ratings.unavailable"))
    organization = load_organization(route[0]) if route else None
    if organization is None:
        raise NotFound(t("ratings.unavailable"))
    context = TenantContext.for_resource(organization, actor_kind=TenantActorKind.MACHINE)
    with tenant_atomic(context):
        request = RatingRequest.objects.select_for_update(of=("self",)).filter(
            Q(completion__transport="WEB") | Q(expires_at__gt=timezone.now()),
            pk=route[1], organization_id=organization.pk, credential_hash=digest,
            sent_at__isnull=False, cancelled_at__isnull=True,
        ).first()
        if request is None:
            raise NotFound(t("ratings.unavailable"))
        yield request, context


def submit_rating(request, context, data):
    value, comment = validate_response(data, request.scale)
    prior = CustomerRating.objects.filter(request=request).first()
    if prior:
        if (prior.value, prior.comment) != (value, comment):
            raise RatingConflict(t("ratings.conflict"))
        return prior, False
    rating = CustomerRating.objects.create(
        organization_id=request.organization_id, request=request, value=value, comment=comment,
    )
    rating.refresh_from_db()
    enqueue_event(DomainEvent(
        aggregate_type="CustomerRating", aggregate_id=str(rating.pk),
        event_type="ratings.received", payload={"ratingId": rating.pk}, tenant_context=context,
    ))
    return rating, True
