"""HTTP status mapping for employee application outcomes."""

from rest_framework.response import Response

STATUSES = {"invalid": 400, "forbidden": 403, "not_found": 404, "conflict": 409}


def response_for(outcome, *, success=200):
    return Response(outcome.data, status=STATUSES[outcome.problem] if outcome.problem else success)
