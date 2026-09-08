# ADR-CHATBALLS-0041: типы уведомлений о платежах удалены вместе с доменом продаж.
from django.db import migrations, models


def drop_payment_notifications(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(type__in=("PAYMENT_RECEIVED", "PAYMENT_FAILED")).delete()
    MessengerBinding = apps.get_model("notifications", "MessengerBinding")
    for binding in MessengerBinding.objects.all():
        push_types = [
            item
            for item in (binding.push_types or [])
            if item not in ("PAYMENT_RECEIVED", "PAYMENT_FAILED")
        ]
        if push_types != binding.push_types:
            binding.push_types = push_types
            binding.save(update_fields=["push_types"])


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0006_alter_messengerbinding_organization_and_more"),
    ]

    operations = [
        migrations.RunPython(drop_payment_notifications, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("DIALOG_WAITING", "Диалог ждёт оператора"),
                    ("DIALOG_NEW_MESSAGE", "Новое сообщение в диалоге"),
                    ("RELEASE_PUBLISHED", "Опубликован релиз агента"),
                    ("INTEGRATION_ERROR", "Ошибка интеграции"),
                    ("LIMIT_REACHED", "Достигнут лимит"),
                ],
                max_length=32,
            ),
        ),
    ]
