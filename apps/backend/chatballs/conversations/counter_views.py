from rest_framework.response import Response

from chatballs.conversations.counter_queries import conversation_counters
from chatballs.conversations.view_base import ConversationViewBase


class ConversationCountersView(ConversationViewBase):
    """Счётчики для дерева фильтров (сайдбар сотрудника / охват админа)."""

    def get(self, request):
        return Response(conversation_counters(request.tenant_context))
