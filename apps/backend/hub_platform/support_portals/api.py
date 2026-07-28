from django.core.exceptions import ValidationError
from rest_framework.response import Response


def validation_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        errors = {
            field: [str(message) for message in messages]
            for field, messages in error.message_dict.items()
        }
        detail = "; ".join(message for messages in errors.values() for message in messages)
        return Response({"detail": detail, "errors": errors}, status=400)
    detail = "; ".join(str(message) for message in error.messages)
    return Response({"detail": detail}, status=400)
