import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ai", "0024_agenttool"), ("conversations", "0031_participant_data")]
    operations = [migrations.CreateModel(
        name="TurnDiagnostic",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("payload", models.JSONField(default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("message", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                            related_name="ai_diagnostic", to="conversations.message")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                               related_name="+", to="identity.organization")),
        ],
    )]
