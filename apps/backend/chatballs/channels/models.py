from django.db import models

# Канал обработки — якорь AI-контекста (ADR-HUB-0019). Группа видимости и
# ссылка на провайдер-интеграцию. Поведение AI (модель, инструкции, знания)
# живёт на агенте канала (ADR-CHATBALLS-0023).


class Channel(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="channels")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    # Группа видимости (ADR-CHATBALLS-0043): новые диалоги канала попадают в неё.
    # NULL — диалоги видны всем сотрудникам.
    group = models.ForeignKey("identity.EmployeeGroup", on_delete=models.SET_NULL, related_name="channels", null=True, blank=True)
    # LLM-провайдер канала (ADR-CHATBALLS-0020).
    provider_integration = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="channels", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Политика канала: остаток от домена продаж — коммерческие флаги всегда
    # выключены (ADR-CHATBALLS-0041/0045), анонимные сессии и самозаявленный контакт
    # используются веб-виджетом и порталом.
    allow_anonymous_sessions = models.BooleanField(default=True)
    allow_self_reported_contact = models.BooleanField(default=True)
    allow_sales_attribution = models.BooleanField(default=False)
    allow_checkout_actions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_channel_org_code"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.code}"
