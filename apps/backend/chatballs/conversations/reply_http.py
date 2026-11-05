"""Render a source application-service outcome at the existing HTTP boundary."""

from rest_framework.response import Response

from chatballs.conversations.reply_problems import ReplyProblem
from chatballs.conversations.serializers import message_payload


def reply_response(outcome):
    if isinstance(outcome, ReplyProblem):
        return Response(outcome.payload, status=outcome.status)
    return Response({"message": message_payload(outcome)}, status=201)
