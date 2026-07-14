import uuid

import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models

import hub_platform.identity.crypto


def backfill_organization_public_ids(apps, schema_editor):
    Organization = apps.get_model("identity", "Organization")
    for organization in Organization.objects.filter(public_id__isnull=True).iterator():
        Organization.objects.filter(pk=organization.pk).update(public_id=uuid.uuid4())


def copy_security_state_to_users(apps, schema_editor):
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    HumanUser = apps.get_model("identity", "HumanUser")
    for profile in EmployeeProfile.objects.all().iterator():
        HumanUser.objects.filter(pk=profile.user_id).update(
            must_change_password=profile.must_change_password,
            totp_enabled=profile.totp_enabled,
            totp_secret=profile.totp_secret,
        )


def copy_security_state_to_profiles(apps, schema_editor):
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    for profile in EmployeeProfile.objects.select_related("user").all().iterator():
        EmployeeProfile.objects.filter(pk=profile.pk).update(
            must_change_password=profile.user.must_change_password,
            totp_enabled=profile.user.totp_enabled,
            totp_secret=profile.user.totp_secret,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0011_enforce_capability_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="must_change_password",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="humanuser",
            name="totp_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="humanuser",
            name="totp_secret",
            field=hub_platform.identity.crypto.EncryptedCharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="organization",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(backfill_organization_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="organization",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.RunPython(copy_security_state_to_users, copy_security_state_to_profiles),
        migrations.RemoveField(
            model_name="employeeprofile",
            name="must_change_password",
        ),
        migrations.RemoveField(
            model_name="employeeprofile",
            name="totp_enabled",
        ),
        migrations.RemoveField(
            model_name="employeeprofile",
            name="totp_secret",
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameModel(
                    old_name="EmployeeProfile",
                    new_name="OrganizationMembership",
                ),
                migrations.AlterModelTable(
                    name="organizationmembership",
                    table="identity_employeeprofile",
                ),
            ],
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="memberships",
                to="identity.organization",
            ),
        ),
        migrations.AlterField(
            model_name="organizationmembership",
            name="primary_department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="memberships",
                to="identity.department",
            ),
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(
                fields=("user", "organization"),
                name="uniq_membership_user_organization",
            ),
        ),
        migrations.CreateModel(
            name="OrganizationInvitation",
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
                ("email", models.EmailField(max_length=254)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("OWNER", "Owner"),
                            ("ADMIN", "Admin"),
                            ("EMPLOYEE", "Employee"),
                        ],
                        max_length=32,
                    ),
                ),
                ("token_hash", models.CharField(max_length=128, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invitations_created",
                        to="identity.organizationmembership",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invitations",
                        to="identity.organization",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="organizationinvitation",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                models.F("organization"),
                condition=models.Q(accepted_at__isnull=True, revoked_at__isnull=True),
                name="uniq_pending_invitation_org_email",
            ),
        ),
    ]
