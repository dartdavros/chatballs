# ADR-HUB-0027 / SPEC-HUB-0018 фаза M1-M2 (этап 1): additive schema + backfill.
# Роли OWNER/ADMIN/EMPLOYEE, обязательная должность (пока nullable), основной отдел
# и размещение владельца на уровне компании. Доступ существующих сотрудников не
# расширяется: OPERATOR → EMPLOYEE, права сохраняются compatibility-адаптером.
import django.db.models.deletion
from django.db import migrations, models


def operator_to_employee(apps, schema_editor):
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    # OPERATOR больше не является системной ролью (ADR-HUB-0027).
    EmployeeProfile.objects.filter(role="OPERATOR").update(role="EMPLOYEE")
    # Владелец всегда на уровне компании: снимаем основной отдел.
    EmployeeProfile.objects.filter(role="OWNER").exclude(primary_department__isnull=True).update(
        primary_department=None
    )


def employee_to_operator(apps, schema_editor):
    # Обратная миграция для rollback до cleanup: EMPLOYEE → OPERATOR.
    # ADMIN и размещение владельца восстановить нельзя — остаются как есть.
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    EmployeeProfile.objects.filter(role="EMPLOYEE").update(role="OPERATOR")


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0006_alter_employeeprofile_totp_secret"),
    ]

    operations = [
        migrations.RenameField(
            model_name="employeeprofile",
            old_name="department",
            new_name="primary_department",
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="position_title",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name="employeeprofile",
            name="role",
            field=models.CharField(
                choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("EMPLOYEE", "Employee")],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="employeeprofile",
            name="primary_department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="employees",
                to="identity.department",
            ),
        ),
        migrations.RunPython(operator_to_employee, employee_to_operator),
        migrations.AddConstraint(
            model_name="employeeprofile",
            constraint=models.CheckConstraint(
                check=models.Q(("role", "OWNER"), _negated=True)
                | models.Q(("primary_department__isnull", True)),
                name="owner_is_company_level",
            ),
        ),
        migrations.AddConstraint(
            model_name="employeeprofile",
            constraint=models.UniqueConstraint(
                condition=models.Q(("role", "OWNER")),
                fields=("organization",),
                name="uniq_owner_per_organization",
            ),
        ),
    ]
