# Администратор установки — глобальный признак учётной записи, а не роль в
# организации: настройки инсталляции (адрес, почта, TURN, хранилище) общие для
# всех организаций, и менять их вправе не любой владелец организации.
#
# Существующие установки: признак получают те, кому мастер первого запуска
# (или bootstrap локального контура) выдал is_superuser — это и есть владелец
# установки. Провижининг через платформенный API суперпользователей не создаёт.
from django.db import migrations, models


def grant_to_setup_owners(apps, schema_editor):
    HumanUser = apps.get_model("identity", "HumanUser")
    HumanUser.objects.filter(is_superuser=True).update(is_instance_admin=True)


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0035_language_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="humanuser",
            name="is_instance_admin",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(grant_to_setup_owners, migrations.RunPython.noop),
    ]
