"""Explicit SMTP test; raw provider exceptions may contain credentials."""
from chatballs.i18n import t
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.instance_settings import email_connection, email_from_address
from chatballs.integrations.action_catalog.authority import require_instance


def check(user, body):
    user = require_instance(user)
    from django.core.mail import send_mail

    connection = email_connection()
    if connection is None:
        return CommandOutcome(
            {"detail": t("settings.smtp_required_first")}, status=400
        )
    recipient = str(body.get("email", "")).strip() or user.email
    try:
        send_mail(
            subject=t("settings.mail_test_subject"),
            message=t("settings.mail_test_body"),
            from_email=email_from_address(),
            recipient_list=[recipient],
            connection=connection,
        )
    except Exception:
        return CommandOutcome({"detail": t("native.instance.email_failed")}, status=400)
    return CommandOutcome({"sent": recipient})
