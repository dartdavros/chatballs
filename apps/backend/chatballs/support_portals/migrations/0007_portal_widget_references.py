import django.db.models.deletion
from django.db import migrations, models


def backfill_widget_references(apps, schema_editor):
    SupportPortal = apps.get_model("support_portals", "SupportPortal")
    SupportPortalProduct = apps.get_model("support_portals", "SupportPortalProduct")
    WebChatWidget = apps.get_model("webchat", "WebChatWidget")

    for portal in SupportPortal.objects.exclude(widget_channel_id=None).iterator():
        matches = list(
            WebChatWidget.objects.filter(
                integration__channel_id=portal.widget_channel_id,
                mode="ANONYMOUS",
            ).order_by("id")[:2]
        )
        if len(matches) == 1:
            portal.widget_id = matches[0].id
            portal.save(update_fields=["widget"])

    for link in SupportPortalProduct.objects.exclude(support_channel_id=None).iterator():
        matches = list(
            WebChatWidget.objects.filter(
                integration__channel_id=link.support_channel_id,
                mode="AUTHENTICATED_PRODUCT",
            ).order_by("id")[:2]
        )
        if len(matches) == 1:
            link.support_widget_id = matches[0].id
            link.save(update_fields=["support_widget"])


class Migration(migrations.Migration):
    dependencies = [
        ("support_portals", "0006_support_portal_widget_channel"),
        ("webchat", "0004_web_chat_widget"),
    ]
    operations = [
        migrations.AddField(
            model_name="supportportal",
            name="widget",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="support_portals", to="webchat.webchatwidget"),
        ),
        migrations.AddField(
            model_name="supportportalproduct",
            name="support_widget",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="support_portal_routes", to="webchat.webchatwidget"),
        ),
        migrations.RunPython(backfill_widget_references, migrations.RunPython.noop),
    ]
