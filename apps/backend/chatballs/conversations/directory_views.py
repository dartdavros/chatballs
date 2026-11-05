from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.directory_queries import DIRECTORY_LIMIT as DIRECTORY_LIMIT
from chatballs.conversations.directory_queries import conversation_directory


class ConversationDirectoryView(APIView):
    """Справочник блока «Диалог» для оператора (дизайн-базлайн v2, кадр G):
    все группы организации — для переноса, активные коллеги — для назначения.
    Доступен любому, кто видит чат: менеджерские списки сотрудников и групп
    сотруднику закрыты, а переносить и назначать он может."""

    permission_classes = [HasCapability]
    required_capabilities = {"GET": "conversations.view"}

    def get(self, request):
        return Response(conversation_directory(request.tenant_context, request.query_params))
