import logging
import os

from django.conf import settings

from chatballs.identity.instance_settings import configured_public_base_url
from chatballs.updates.check_in_client import send_check_in
from chatballs.updates.check_in_state import finish_attempt, reserve_attempt, still_allowed

logger = logging.getLogger(__name__)


def check_in_if_due() -> None:
    version = os.environ.get("CHATBALLS_VERSION", settings.CHATBALLS_VERSION)
    attempt = reserve_attempt(version)
    if attempt is None:
        return
    public_url = configured_public_base_url()
    if not still_allowed(attempt):
        return
    result = send_check_in(attempt.installation_id, version, public_url)
    if finish_attempt(attempt, result) and result.error:
        logger.warning("Backoffice check-in failed: %s", result.error)
