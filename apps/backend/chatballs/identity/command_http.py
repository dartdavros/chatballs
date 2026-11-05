"""Preserve the existing HTTP contract of shared administrative commands."""

from rest_framework.response import Response


def command_response(outcome):
    return Response(outcome.data, status=outcome.status)
