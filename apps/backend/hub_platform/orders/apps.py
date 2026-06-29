from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "orders"
    name = "hub_platform.orders"
    verbose_name = "Orders"
