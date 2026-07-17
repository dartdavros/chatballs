from django.db import migrations, models


def configure_managed_ai_tokens(apps, schema_editor):
    apps.get_model("subscriptions", "QuotaDefinition").objects.filter(
        key="managed_ai_credits"
    ).update(accounting_scale=1000, accounting_unit="tokens")


def restore_credit_accounting(apps, schema_editor):
    apps.get_model("subscriptions", "QuotaDefinition").objects.filter(
        key="managed_ai_credits"
    ).update(accounting_scale=1, accounting_unit="")


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0006_business_managed_ai_credits")]

    operations = [
        migrations.AddField(
            model_name="quotadefinition",
            name="accounting_scale",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="quotadefinition",
            name="accounting_unit",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="usagereservation",
            name="quantity",
            field=models.PositiveBigIntegerField(default=1),
        ),
        migrations.RunPython(configure_managed_ai_tokens, restore_credit_accounting),
    ]
