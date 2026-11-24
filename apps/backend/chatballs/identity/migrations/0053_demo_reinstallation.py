from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0052_demo_inactivity_protection")]

    operations = [
        migrations.AddField(
            model_name="demodataset", name="generation",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="demodataset", name="reinstall_request_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="demodataset", name="reinstall_finished_at",
            field=models.DateTimeField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="demodataset", name="reinstall_error",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AlterField(
            model_name="demodataset", name="status",
            field=models.CharField(
                choices=[
                    ("INSTALLING", "Устанавливается"), ("INSTALLED", "Установлены"),
                    ("REINSTALLING", "Переустанавливаются"), ("REMOVING", "Удаляются"),
                    ("FAILED", "Ошибка"),
                ],
                default="INSTALLING", max_length=16,
            ),
        ),
    ]
