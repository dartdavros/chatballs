"""Report actions use the same scoped selectors as each product report."""

from chatballs.conversations.report_directory import report_directory
from chatballs.conversations.stats import sales_overview_stats
from chatballs.conversations.support_filters import parse_filters
from chatballs.conversations.support_report import calculate_support_report
from chatballs.integrations.action_catalog.feedback_values import support_payload
from chatballs.integrations.action_catalog.report_results import ACCESS, OVERVIEW, SUPPORT
from chatballs.integrations.action_catalog.report_schemas import FILTERS
from chatballs.integrations.action_catalog.schema import action, enum, obj
from chatballs.integrations.adapters.contracts import OperationResult, ResultState


def overview(context, values):
    return OperationResult(ResultState.COMPLETED, sales_overview_stats(context.tenant, values.get("period", "today")))


def access(context, values):
    return OperationResult(ResultState.COMPLETED, report_directory(context.tenant))


def support(context, values):
    return OperationResult(ResultState.COMPLETED, support_payload(
        calculate_support_report(context=context.tenant, filters=parse_filters(values))))


for key, title, inputs, output, handler, route, view, capability in (
    ("overview.get", "native.report_overview", obj(period=enum(("today", "d7", "d30"), "native.report_period")),
        OVERVIEW, overview, "stats/", "reporting_views.ConversationStatsView", "conversations.view"),
    ("access.get", "native.report_access", obj(), ACCESS, access,
        "support-report/access/", "support_views.SupportReportAccessView", ""),
    ("support.get", "native.report_support", FILTERS, SUPPORT,
        support, "support-report/", "support_views.SupportReportView", ""),
):
    action(key=f"reports.{key}", title=title, input=inputs, output=output, handler=handler, capability=capability,
        scope="organization", route=f"conversations/{route}", view=f"chatballs.conversations.{view}", method="GET")
