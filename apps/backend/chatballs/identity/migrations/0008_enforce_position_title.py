# ADR-HUB-0027 / SPEC-HUB-0018 фаза M2 (этап 1): после явного заполнения должностей
# включается обязательность. Оставшиеся незаполненные значения нормализуются в "";
# непустая должность гарантируется application contract (SPEC-CHATBALLS-0016 §5).
from django.db import migrations, models


def coalesce_null_titles(apps, schema_editor):
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    EmployeeProfile.objects.filter(position_title__isnull=True).update(position_title="")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0007_employee_roles_position_department"),
    ]

    operations = [
        migrations.RunPython(coalesce_null_titles, noop),
        migrations.AlterField(
            model_name="employeeprofile",
            name="position_title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
