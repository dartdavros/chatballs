"""Guard-функции C04 должны видеть строки поверх RLS (SECURITY DEFINER).

Функции проверяют целостность связей между тенантами и обязаны читать
родительскую строку независимо от политик вызывающей роли. Как SECURITY
INVOKER их внутренний SELECT подчинялся RLS: из кросс-тенантного пути без
выставленного `chatballs.organization_id` (outbox-воркер claim'ит событие
любой организации) родитель не виден, parent_org = NULL, и проверка
`IS DISTINCT FROM` ложно срабатывала — легитимный UPDATE падал с
`cross-tenant relation`, что уводило воркер в краш-петлю.

SECURITY DEFINER исполняет их от chatballs_schema (policy USING (true)),
поэтому сравнение идёт по фактическим данным. Проверка не ослабляется:
настоящее нарушение по-прежнему приводит к RAISE. search_path закреплён,
как того требует безопасность SECURITY DEFINER-функций.
"""

from django.db import migrations


GUARD_FUNCTIONS = (
    "chatballs.enforce_tenant_fk()",
    "chatballs.enforce_tenant_user()",
    "chatballs.enforce_tenant_pair()",
)


def set_security_definer(apps, schema_editor):
    for function in GUARD_FUNCTIONS:
        schema_editor.execute(
            f"ALTER FUNCTION {function} SECURITY DEFINER SET search_path = public, pg_temp"
        )


def set_security_invoker(apps, schema_editor):
    for function in GUARD_FUNCTIONS:
        schema_editor.execute(
            f"ALTER FUNCTION {function} SECURITY INVOKER RESET search_path"
        )


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0008_ai_knowledge_scope_guards")]
    operations = [migrations.RunPython(set_security_definer, set_security_invoker)]
