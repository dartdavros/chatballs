import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integrations", "0023_scenariobudget_payload_bytes_and_more")]
    operations = [
        migrations.AlterField(model_name="actiongrant", name="integration",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                to="integrations.integration")),
        migrations.AddField(model_name="actiongrant", name="native_key",
            field=models.CharField(blank=True, default="", max_length=100)),
        migrations.AddConstraint(model_name="actiongrant", constraint=models.UniqueConstraint(
            fields=("membership", "native_key"), condition=models.Q(integration__isnull=True),
            name="native_operation_grant")),
        migrations.AddConstraint(model_name="actiongrant", constraint=models.CheckConstraint(
            condition=(models.Q(integration__isnull=False, native_key="") & ~models.Q(operation_key="")
                | models.Q(integration__isnull=True, operation_key="") & ~models.Q(native_key="")),
            name="action_grant_exact_target")),
        migrations.CreateModel(name="NativeEffectReceipt", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("content", models.TextField()),
            ("invocation_digest", models.CharField(max_length=64)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name="+", to="identity.organization")),
            ("step", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                related_name="native_receipt", to="integrations.scenariostep")),
        ]),
    ]
