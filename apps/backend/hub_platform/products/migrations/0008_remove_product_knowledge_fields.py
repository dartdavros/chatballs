# ADR-HUB-0023: содержательное описание продукта живёт в Знаниях; продукт —
# техническая запись-якорь (токены, офферы, каналы).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0007_product_support_token_secret"),
    ]

    operations = [
        migrations.RemoveField(model_name="product", name="summary"),
        migrations.RemoveField(model_name="product", name="sales_description"),
    ]
