# Приглашение существующего пользователя во вторую организацию: вместо ошибки
# «e-mail занят» администратор выписывает приглашение с той же ролью,
# должностью, телефоном и группами, что и при создании сотрудника. Членство
# создаётся из этих полей в момент принятия, а не в момент приглашения.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0036_humanuser_is_instance_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationinvitation",
            name="position_title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="organizationinvitation",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="organizationinvitation",
            name="group_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
