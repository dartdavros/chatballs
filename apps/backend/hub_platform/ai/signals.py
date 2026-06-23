from django.db.models.signals import post_save
from django.dispatch import receiver

from hub_platform.ai.models import AIAgent
from hub_platform.products.models import Product


@receiver(post_save, sender=Product, dispatch_uid="ai_create_agent_for_product")
def create_agent_for_product(sender, instance, created, **kwargs) -> None:
    # Инвариант ADR-HUB-0007: ровно один sales-агент на продукт.
    if created:
        AIAgent.objects.get_or_create(product=instance, defaults={"name": f"{instance.name} Sales Agent"})
