# ADR-HUB-0041: коммерческий слой каталога (Offer/Price/MarketplacePublication)
# и ingest-токен вебхука заказов удаляются вместе с доменом продаж.
# Зависимость от tenancy.0017: сначала снимаются таблицы orders_*/sales_*,
# ссылавшиеся на products_offer/products_price.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0010_alter_marketplacepublication_organization_and_more"),
        ("tenancy", "0017_drop_commerce"),
    ]

    operations = [
        migrations.RemoveField(model_name="product", name="ingest_token_hash"),
        migrations.DeleteModel(name="MarketplacePublication"),
        migrations.DeleteModel(name="Price"),
        migrations.DeleteModel(name="Offer"),
    ]
