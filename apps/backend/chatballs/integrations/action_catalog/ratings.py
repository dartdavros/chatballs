"""Grants never replace a customer's live rating credential or vote rules."""

from django.utils.translation import override

from chatballs.i18n import customer_language
from chatballs.integrations.action_catalog.rating_schemas import (
    CARD,
    INTEGER,
    QUESTION,
    RESULT,
    RESULTS,
    SCORE,
    SETTINGS,
    SETTINGS_FIELDS,
)
from chatballs.integrations.action_catalog.schema import (
    CONVERSATION_ID,
    action,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.ratings import queries
from chatballs.ratings.card import conversation_card
from chatballs.ratings.public_service import (
    question_payload,
    resolved_request,
    result_payload,
    submit_rating,
)
from chatballs.ratings.settings_service import settings_payload, update_settings


def settings(context, values):
    return OperationResult(ResultState.COMPLETED, queries.settings(context.tenant))


def configure(context, values):
    return OperationResult(ResultState.COMPLETED, settings_payload(update_settings(context.tenant, values)))


def results(context, values):
    data = queries.results(context.tenant, values)
    for group in data["scaleGroups"]:
        group["values"] = [{"value": int(value), "count": count} for value, count in group["values"].items()]
    return OperationResult(ResultState.COMPLETED, data)


def conversation(context, values):
    return OperationResult(ResultState.COMPLETED, conversation_card(context.tenant, values["conversation_id"]))


def question(context, values):
    with resolved_request(values["credential"], expected_organization_id=context.tenant.organization_id) as (target, _tenant):
        context.require_conversation(target.conversation_id)
        return OperationResult(ResultState.COMPLETED, question_payload(target))


def respond(context, values):
    with resolved_request(values["credential"], expected_organization_id=context.tenant.organization_id) as (target, tenant):
        context.require_conversation(target.conversation_id)
        with override(customer_language(tenant.organization)):
            result, _created = submit_rating(target, tenant, {key: value for key, value in values.items() if key != "credential"})
        return OperationResult(ResultState.COMPLETED, result_payload(result))


CREDENTIAL = TypeSpec("string", secret=True, required=True, title_key="native.rating_credential")
for key, title, inputs, output, handler, route, view, method, capability, scope in (
    ("settings.get", "native.rating_settings_read", obj(), SETTINGS, settings,
        "ratings/settings/", "tenant_views.RatingSettingsView", "GET", "settings.manage", "organization"),
    ("settings.patch", "native.rating_settings_change", obj(**SETTINGS_FIELDS), SETTINGS, configure,
        "ratings/settings/", "tenant_views.RatingSettingsView", "PATCH", "settings.manage", "organization"),
    ("results.get", "native.rating_results", obj(responderId=INTEGER, groupId=INTEGER, after=TypeSpec("datetime"),
        before=TypeSpec("datetime"), offset=INTEGER, limit=INTEGER), RESULTS, results,
        "ratings/results/", "tenant_views.RatingResultsView", "GET", "", "organization"),
    ("conversation.get", "native.rating_conversation", obj(conversation_id=CONVERSATION_ID), CARD, conversation,
        "ratings/conversations/<int:conversation_id>/", "tenant_views.ConversationRatingsView", "GET", "", "conversation"),
    ("customer.get", "native.rating_question", obj(credential=CREDENTIAL), QUESTION, question,
        "api/v1/ratings/", "public_views.PublicRatingView", "GET", "", "conversation"),
    ("customer.post", "native.rating_respond", obj(credential=CREDENTIAL, value=required(SCORE),
        comment=TypeSpec("string", max_length=2000)), RESULT, respond,
        "api/v1/ratings/", "public_views.PublicRatingView", "POST", "", "conversation"),
):
    action(key=f"ratings.{key}", title=title, input=inputs, output=output, handler=handler, capability=capability,
        scope=scope, route=route, view=f"chatballs.ratings.{view}", method=method)
