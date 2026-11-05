"""Domain command outcome shared by HTTP and the native catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandOutcome:
    data: dict
    status: int = 200


def validation_outcome(error):
    from chatballs.i18n import t

    if hasattr(error, "message_dict"):
        errors = {key: values[0] if isinstance(values, list) else str(values)
            for key, values in error.message_dict.items()}
        if "__all__" in errors:
            errors["password"] = " ".join(error.message_dict["__all__"])
            del errors["__all__"]
        return CommandOutcome({"detail": next(iter(errors.values()), t("setup.check_fields")), "errors": errors}, status=400)
    message = " ".join(error.messages)
    return CommandOutcome({"detail": message, "errors": {"password": message}}, status=400)
