# ADR-HUB-0045: сущность Product удалена целиком. Миграция сохранена пустой —
# на неё ссылаются следующие миграции identity.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0004_employeeprofile_phone"),
    ]

    operations = []
