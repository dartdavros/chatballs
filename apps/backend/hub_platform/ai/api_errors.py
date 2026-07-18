from django.core.exceptions import ValidationError
from rest_framework.response import Response


def validation_error_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        detail = "; ".join(
            message
            for messages in error.message_dict.values()
            for message in messages
        )
    else:
        detail = "; ".join(error.messages)
    return Response({"detail": detail}, status=400)
