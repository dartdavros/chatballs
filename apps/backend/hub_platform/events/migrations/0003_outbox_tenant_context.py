from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0002_rename_events_outb_status_881ef5_idx_events_outb_status_9dabce_idx_and_more"),
        ("identity", "0012_membership_identity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxevent",
            name="actor_kind",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="outboxevent",
            name="actor_user",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="outbox_events", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="outboxevent",
            name="membership",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="outbox_events", to="identity.organizationmembership"),
        ),
        migrations.AddField(
            model_name="outboxevent",
            name="organization",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="outbox_events", to="identity.organization"),
        ),
        migrations.AddField(
            model_name="outboxevent",
            name="ownership",
            field=models.CharField(choices=[("PLATFORM", "Platform"), ("TENANT", "Tenant")], db_index=True, default="PLATFORM", max_length=16),
        ),
    ]
