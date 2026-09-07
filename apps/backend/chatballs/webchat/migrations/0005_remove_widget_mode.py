# ADR-HUB-0045: авторизованный in-product чат удалён вместе с сущностью Product,
# и режим виджета перестал что-либо различать — поле снимается целиком.
#
# Зависит от tenancy/0029: та миграция удаляет строки виджетов режима
# AUTHENTICATED_PRODUCT по этой же колонке, поэтому колонка должна дожить до неё.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("webchat", "0004_web_chat_widget"),
        ("tenancy", "0029_drop_product_support"),
    ]

    operations = [
        migrations.RemoveField(model_name="webchatwidget", name="mode"),
    ]
