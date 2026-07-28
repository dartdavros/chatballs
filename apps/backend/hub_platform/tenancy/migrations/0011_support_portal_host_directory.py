from django.db import migrations


FORWARD_SQL = """
DROP VIEW custocrm.support_portal_directory;
CREATE VIEW custocrm.support_portal_directory
WITH (security_barrier = true) AS
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.hosted_domain AS lookup_key
    FROM support_portals_supportportal portal
    JOIN identity_department department
      ON department.id = portal.department_id
     AND department.organization_id = portal.organization_id
    WHERE portal.status = 'PUBLISHED'
      AND department.code = 'support'
    UNION ALL
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.custom_domain AS lookup_key
    FROM support_portals_supportportal portal
    JOIN identity_department department
      ON department.id = portal.department_id
     AND department.organization_id = portal.organization_id
    WHERE portal.status = 'PUBLISHED'
      AND department.code = 'support'
      AND portal.custom_domain <> ''
      AND portal.custom_domain_verified_at IS NOT NULL;
ALTER VIEW custocrm.support_portal_directory OWNER TO custocrm_schema;
REVOKE ALL ON custocrm.support_portal_directory FROM PUBLIC;
GRANT SELECT ON custocrm.support_portal_directory TO custocrm_runtime_platform;
"""

REVERSE_SQL = """
DROP VIEW custocrm.support_portal_directory;
CREATE VIEW custocrm.support_portal_directory
WITH (security_barrier = true) AS
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.slug AS lookup_key
    FROM support_portals_supportportal portal
    JOIN identity_department department
      ON department.id = portal.department_id
     AND department.organization_id = portal.organization_id
    WHERE portal.status = 'PUBLISHED'
      AND department.code = 'support';
ALTER VIEW custocrm.support_portal_directory OWNER TO custocrm_schema;
REVOKE ALL ON custocrm.support_portal_directory FROM PUBLIC;
GRANT SELECT ON custocrm.support_portal_directory TO custocrm_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0010_support_portal_guards"),
        ("support_portals", "0004_portal_domains"),
    ]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
