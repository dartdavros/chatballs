# SPEC-HUB-0027 §3.2/§12, ADR-HUB-0037 §7 — этап 3.
#
# Приводит существующие каналы в соответствие P1-P2 и меняет дефолты модели,
# которые сами по себе их нарушали: attribution и checkout были включены по
# умолчанию.
#
# Решение владельца по унаследованным каналам: выключить checkout и
# attribution. Продуктовая часть инвариантов (P3-P5) снята вместе с сущностью
# Product (ADR-CHATBALLS-0041).
from django.db import migrations, models


def relax_non_product_channels(apps, schema_editor):
    Channel = apps.get_model("channels", "Channel")

    Channel.objects.filter(
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
