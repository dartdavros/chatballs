# Generated for CustoAI / BYOK credential mode (ADR-HUB-0033 §4, SPEC-HUB-0024 §2).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0007_remove_aiagent_is_active_aiagent_lifecycle_version_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiagent',
            name='credential_mode',
            field=models.CharField(
                choices=[('CUSTOAI', 'CustoAI (Managed)'), ('BYOK', 'BYOK')],
                default='CUSTOAI',
                max_length=16,
            ),
        ),
    ]
