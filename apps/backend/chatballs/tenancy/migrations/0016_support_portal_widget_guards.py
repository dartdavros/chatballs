from django.db import migrations


FORWARD_SQL = """
CREATE CONSTRAINT TRIGGER sp_portal_widget
AFTER INSERT OR UPDATE ON support_portals_supportportal
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('webchat_webchatwidget', 'widget_id');

CREATE CONSTRAINT TRIGGER sp_product_support_widget
AFTER INSERT OR UPDATE ON support_portals_supportportalproduct
DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION
chatballs.enforce_tenant_fk('webchat_webchatwidget', 'support_widget_id');
"""


REVERSE_SQL = """
DROP TRIGGER IF EXISTS sp_product_support_widget
    ON support_portals_supportportalproduct;
DROP TRIGGER IF EXISTS sp_portal_widget ON support_portals_supportportal;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0015_web_chat_widget_ingress"),
        ("support_portals", "0007_portal_widget_references"),
    ]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
