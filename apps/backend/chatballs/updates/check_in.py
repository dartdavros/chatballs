import logging
import os

from django.conf import settings

from chatballs.updates.check_in_client import send_check_in
from chatballs.updates.check_in_state import finish_attempt, reserve_attempt, still_allowed

logger = logging.getLogger(__name__)


def check_in_if_due() -> None:
    attempt = reserve_attempt()
    if attempt is None or not still_allowed(attempt):
        return
    version = os.environ.get("CHATBALLS_VERSION", settings.CHATBALLS_VERSION)
    result = send_check_in(attempt.installation_id, version)
    if finish_attempt(attempt, result) and result.error:
        logger.warning("Backoffice check-in failed: %s", result.error)
