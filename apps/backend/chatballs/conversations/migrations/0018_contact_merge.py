from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0017_conversation_note_author"),
        ("identity", "0025_humanuser_totp_last_used_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="merged_into",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="merged_contacts", to="conversations.contact"),
        ),
        migrations.CreateModel(
            name="ContactMerge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                ("moved_identity_ids", models.JSONField(blank=True, default=list)),
                ("moved_conversation_ids", models.JSONField(blank=True, default=list)),
                ("filled_fields", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reverted_at", models.DateTimeField(blank=True, null=True)),
                ("revert_reason", models.TextField(blank=True, default="")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contact_merges", to="identity.organization")),
                ("reverted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="merges_out", to="conversations.contact")),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="merges_in", to="conversations.contact")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
