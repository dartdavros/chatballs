from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("support_portals", "0008_remove_supportportal_department")]

    operations = [
        migrations.AddField(
            model_name="supportportal",
            name="theme",
            field=models.CharField(default="classic", max_length=64),
        ),
        migrations.AddField(
            model_name="supportportal",
            name="theme_scheme",
            field=models.CharField(
                choices=[
                    ("LIGHT", "Светлая"),
                    ("DARK", "Тёмная"),
                    ("SYSTEM", "Как в системе"),
                ],
                default="LIGHT",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="supportportal",
            name="theme_settings",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddConstraint(
            model_name="supportportal",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    theme_scheme__in=["LIGHT", "DARK", "SYSTEM"]
                ),
                name="support_portal_theme_scheme_valid",
            ),
        ),
    ]
