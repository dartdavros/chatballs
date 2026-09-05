# SPEC-HUB-0027 §3.2/§12, ADR-HUB-0037 §7 — этап 3.
#
# Приводит существующие каналы в соответствие P1-P5 и меняет дефолты модели,
# которые сами по себе нарушали P1-P2: канал создаётся без продукта, а
# attribution и checkout были включены по умолчанию.
#
# Решение владельца по унаследованным непродуктовым каналам: выключить
# checkout и attribution, а не назначать продукт. Поэтому миграция чинит ровно
# P1 и P2. Нарушения P3-P5 она не трогает и останавливает выкат: их
# исправление меняет смысл канала (обязательная идентичность), и выбирать за
# владельца здесь нельзя.
from django.db import migrations, models


def relax_non_product_channels(apps, schema_editor):
    Channel = apps.get_model("channels", "Channel")

    blocked = list(
        Channel.objects.filter(requires_authenticated_product_identity=True)
        .filter(
            models.Q(product__isnull=True)
            | models.Q(allow_anonymous_sessions=True)
            | models.Q(allow_self_reported_contact=True)
        )
        .values_list("id", "code")
    )
    if blocked:
        listed = ", ".join(f"{code} (id={channel_id})" for channel_id, code in blocked)
        raise RuntimeError(
            "Каналы нарушают P3-P5 и требуют решения владельца до включения "
            f"инвариантов: {listed}"
        )

    Channel.objects.filter(product__isnull=True).filter(
        models.Q(allow_checkout_actions=True) | models.Q(allow_sales_attribution=True)
    ).update(allow_checkout_actions=False, allow_sales_attribution=False)


def noop(apps, schema_editor):
    # Прежние значения не восстанавливаются: они были нарушением инварианта.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0004_remove_channel_ai_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='allow_checkout_actions',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='channel',
            name='allow_sales_attribution',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(relax_non_product_channels, noop),
    ]
