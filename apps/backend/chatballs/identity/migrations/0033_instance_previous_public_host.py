"""Прежний адрес установки остаётся принятым после смены адреса.

Владелец меняет адрес в «Настройках» заранее — до того, как новый домен начал
резолвиться и получил сертификат, — и сидит при этом на старом. Пока принятым
был только новый адрес, сохранение выбрасывало его из установки через десять
секунд (TTL кэша), а мастер первого запуска уже закрыт: вернуться было неоткуда.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0032_remove_organization_tax_regime_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="instancesettings",
            name="previous_public_host",
            field=models.CharField(blank=True, default="", max_length=253),
        ),
    ]
