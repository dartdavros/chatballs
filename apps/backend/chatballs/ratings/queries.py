"""Protected rating queries shared by HTTP and scenario operations."""

from rest_framework import serializers

from chatballs.conversations.management_scope import management_scope
from chatballs.ratings.models import RatingSettings
from chatballs.ratings.results import protected_payload, results_for_context, scale_groups
from chatballs.ratings.settings_service import require_admin, settings_payload


class ResultFilters(serializers.Serializer):
    responderId = serializers.IntegerField(min_value=1, required=False)
    groupId = serializers.IntegerField(min_value=1, required=False)
    after = serializers.DateTimeField(required=False)
    before = serializers.DateTimeField(required=False)
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


def settings(context):
    require_admin(context)
    policy = RatingSettings.objects.filter(organization_id=context.organization_id).first()
    return settings_payload(policy or RatingSettings(organization_id=context.organization_id))


def results(context, parameters):
    rows = results_for_context(context)
    filters = ResultFilters(data=parameters)
    filters.is_valid(raise_exception=True)
    data = filters.validated_data
    staff_ids = management_scope(context, forbidden_key="ratings.forbidden").staff_ids()
    if "responderId" in data:
        rows = rows.filter(request__responder_ids__contains=[data["responderId"]]) if data["responderId"] in staff_ids else rows.none()
    if "groupId" in data:
        rows = rows.filter(request__conversation__group_id=data["groupId"])
    if "after" in data:
        rows = rows.filter(received_at__gte=data["after"])
    if "before" in data:
        rows = rows.filter(received_at__lt=data["before"])
    offset, limit = data["offset"], data["limit"]
    return {"count": rows.count(), "scaleGroups": scale_groups(rows.iterator()),
            "results": [protected_payload(row, permitted_staff_ids=staff_ids) for row in rows[offset:offset + limit]]}
