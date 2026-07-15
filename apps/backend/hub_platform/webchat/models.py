from django.db import models

from hub_platform.tenancy.models import TenantRelationModel

# Анонимная браузерная сессия Web Chat (SPEC-HUB-0003 §7). Храним только hash
# токена; токен живёт в браузере и идентифицирует ConnectionIdentity канала.


class WebSession(TenantRelationModel):
    tenant_relation_fields = ("connection", "identity")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    connection = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="web_sessions")
    identity = models.ForeignKey("conversations.ConnectionIdentity", on_delete=models.CASCADE, related_name="web_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"websession:{self.identity_id}"
