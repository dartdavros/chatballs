"""Shared transfer reason contract."""

from rest_framework import serializers


class ReasonInput(serializers.Serializer):
    code = serializers.RegexField(r"^[-a-zA-Z0-9_]+$", max_length=64, required=False)
    name = serializers.CharField(max_length=120)
    isActive = serializers.BooleanField(required=False, source="is_active")
