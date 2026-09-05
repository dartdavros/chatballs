from django.db import migrations, models


class Migration(migrations.Migration):
    """C07 SPEC §10: track in-flight storage upload reservations so a multi-step
    upload can reserve the expected size, finalize the actual size and release the
    reservation on failure without exceeding the storage_bytes quota."""

    dependencies = [
        ("identity", "0015_organization_status"),
        ("tenancy", "0005_platform_provisioning_grants"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationstorageusage",
            name="reserved_bytes",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name="organizationstorageusage",
            constraint=models.CheckConstraint(
                condition=models.Q(reserved_bytes__gte=0),
                name="storage_usage_reserved_non_negative",
            ),
        ),
        migrations.CreateModel(
            name="StorageReservation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("idempotency_key", models.CharField(max_length=160)),
                ("reserved_bytes", models.PositiveBigIntegerField()),
                ("finalized", models.BooleanField(default=False)),
                ("released", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.PROTECT,
                        related_name="storage_reservations",
                        to="identity.organization",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(finalized=False, released=False),
                        fields=["organization", "idempotency_key"],
                        name="uniq_storage_reservation_active",
                    )
                ]
            },
        ),
    ]
