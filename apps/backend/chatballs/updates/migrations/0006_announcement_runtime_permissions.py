from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("updates", "0005_announcement_state")]

    operations = [
        migrations.RunSQL(
            "GRANT SELECT, INSERT, UPDATE ON updates_announcementstate TO chatballs_runtime_app;",
            "REVOKE SELECT, INSERT, UPDATE ON updates_announcementstate FROM chatballs_runtime_app;",
        ),
    ]
