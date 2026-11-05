"""Native results follow the initiator's language outside HTTP requests too."""

from django.utils.translation import override

from chatballs.i18n import customer_language, first_chosen


def native_locale(tenant):
    language = first_chosen(getattr(tenant.actor_user, "ui_language", ""))
    return override(language or customer_language(tenant.organization))
