# SPEC-HUB-0027 §5.1/§5.3, ADR-HUB-0037 §9 — этап 1.
#
# Вводит `channels.view` / `channels.manage` и выдаёт их существующим профилям
# доступа по текущим `ai.view` / `ai.manage`, чтобы никто не потерял доступ в
# момент выката.
#
# Scope в этой модели живёт на `EmployeeAccessAssignment`, а capability — на
# `AccessProfile`. Поэтому «с тем же scope» достигается тем, что мы вообще не
# трогаем назначения: каждое действующее назначение профиля продолжает работать
# со своим scope. Обе новые capability допускают ORGANIZATION и DEPARTMENT, так
# что набор допустимых scope профиля (`allowed_profile_scopes`) не сужается.
from django.db import migrations, models

AI_VIEW = "ai.view"
AI_MANAGE = "ai.manage"
CHANNELS_VIEW = "channels.view"
CHANNELS_MANAGE = "channels.manage"


def _grant(apps, *, source: str, target: str) -> None:
    AccessProfile = apps.get_model("identity", "AccessProfile")
    AccessProfileCapability = apps.get_model("identity", "AccessProfileCapability")

    already_granted = set(
        AccessProfileCapability.objects.filter(capability_code=target).values_list(
            "access_profile_id", flat=True
        )
    )
    # organization_id берётся у профиля, а не выводится: триггер
    # custocrm.enforce_tenant_fk требует совпадения с владельцем профиля.
    profiles = (
        AccessProfile.objects.filter(capability_links__capability_code=source)
        .values_list("id", "organization_id")
        .distinct()
    )
    AccessProfileCapability.objects.bulk_create(
        [
            AccessProfileCapability(
                access_profile_id=profile_id,
                organization_id=organization_id,
                capability_code=target,
            )
            for profile_id, organization_id in profiles
            if profile_id not in already_granted
        ]
    )


def grant_channel_capabilities(apps, schema_editor):
    _grant(apps, source=AI_VIEW, target=CHANNELS_VIEW)
    _grant(apps, source=AI_MANAGE, target=CHANNELS_MANAGE)


def revoke_channel_capabilities(apps, schema_editor):
    # В отличие от 0010 откат обязан удалить выданные строки: следом
    # восстанавливается прежний check-constraint реестра, и строки с кодом вне
    # списка сделали бы обратную миграцию невыполнимой.
    AccessProfileCapability = apps.get_model("identity", "AccessProfileCapability")
    AccessProfileCapability.objects.filter(
        capability_code__in=(CHANNELS_VIEW, CHANNELS_MANAGE)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('identity', '0015_organization_status'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='accessprofilecapability',
            name='access_profile_capability_registry',
        ),
        migrations.AddConstraint(
            model_name='accessprofilecapability',
            constraint=models.CheckConstraint(condition=models.Q(('capability_code__in', ['company.view', 'company.manage', 'departments.view', 'departments.manage', 'employees.view', 'employees.manage', 'products.view', 'products.manage', 'channels.view', 'channels.manage', 'ai.view', 'ai.manage', 'ai.publish', 'integrations.view', 'integrations.manage', 'secrets.manage', 'settings.view', 'settings.manage', 'audit.view', 'conversations.view', 'conversations.operate', 'conversations.call', 'customers.view', 'customers.manage', 'sales.view', 'sales.operate', 'sales.correct', 'sales_sources.manage', 'support.view', 'support.operate', 'notifications.manage'])), name='access_profile_capability_registry'),
        ),
        # Порядок важен: при откате Django исполняет операции в обратном порядке,
        # поэтому строки удаляются до восстановления старого constraint.
        migrations.RunPython(grant_channel_capabilities, revoke_channel_capabilities),
    ]
