"""Shared validation for participation requests."""

from rest_framework import serializers

from chatballs.i18n import t


class JoinInput(serializers.Serializer):
    membershipId = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()

class LeaveInput(serializers.Serializer):
    reason = serializers.CharField()

class LimitInput(serializers.Serializer):
    additionalParticipantLimit = serializers.IntegerField(
        min_value=1, max_value=10,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["additionalParticipantLimit"]
        for key in ("min_value", "max_value", "invalid", "required", "null"):
            field.error_messages[key] = t("participants.limit_range")
        for validator in field.validators:
            if hasattr(validator, "limit_value"):
                validator.message = t("participants.limit_range")
