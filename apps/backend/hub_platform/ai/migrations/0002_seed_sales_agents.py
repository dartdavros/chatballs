from django.db import migrations


def seed_agents(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    AIAgent = apps.get_model("ai", "AIAgent")
    for product in Product.objects.all():
        AIAgent.objects.get_or_create(product=product, defaults={"name": f"{product.name} Sales Agent"})


def remove_agents(apps, schema_editor):
    apps.get_model("ai", "AIAgent").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("products", "0001_move_product_state"),
    ]

    operations = [migrations.RunPython(seed_agents, remove_agents)]
