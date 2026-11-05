"""Named bounded pagination schemas shared across native product domains."""

from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import TypeSpec

PAGE_INPUTS = {"page": TypeSpec("integer"), "pageSize": TypeSpec("integer")}


def page_of(item):
    return obj(items=TypeSpec("array", items=item), page=TypeSpec("integer"),
        pageSize=TypeSpec("integer"), total=TypeSpec("integer"), pageCount=TypeSpec("integer"))
