# ADR-HUB-0043: у портала больше нет отдела. Дроп колонки department_id
# (support_portals/0008) каскадно унёс вьюху custocrm.support_portal_directory —
# пересоздаём её без join на отделы и снимаем стейл-триггер sp_portal_department.
from django.db import migrations

FORWARD_SQL = """
DROP TRIGGER IF EXISTS sp_portal_department ON support_portals_supportportal;
DROP VIEW IF EXISTS custocrm.support_portal_directory;
CREATE VIEW custocrm.support_portal_directory
WITH (security_barrier = true) AS
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.hosted_domain AS lookup_key
    FROM support_portals_supportportal portal
    WHERE portal.status = 'PUBLISHED'
    UNION ALL
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.custom_domain AS lookup_key
    FROM support_portals_supportportal portal
    WHERE portal.status = 'PUBLISHED'
      AND portal.custom_domain <> ''
      AND portal.custom_domain_verified_at IS NOT NULL;
ALTER VIEW custocrm.support_portal_directory OWNER TO custocrm_schema;
REVOKE ALL ON custocrm.support_portal_directory FROM PUBLIC;
GRANT SELECT ON custocrm.support_portal_directory TO custocrm_runtime_platform;
"""

# На откате колонка department_id ещё не восстановлена (support_portals/0008
# разворачивается позже этой миграции), поэтому старую версию вьюхи собрать
# нельзя. Оставляем безотдельную: reverse tenancy/0011 делает DROP VIEW без
# IF EXISTS и требует, чтобы вьюха существовала.
REVERSE_SQL = """
DROP VIEW IF EXISTS custocrm.support_portal_directory;
CREATE VIEW custocrm.support_portal_directory
WITH (security_barrier = true) AS
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.hosted_domain AS lookup_key
    FROM support_portals_supportportal portal
    WHERE portal.status = 'PUBLISHED'
    UNION ALL
    SELECT portal.id AS resource_id,
           portal.organization_id,
           portal.custom_domain AS lookup_key
    FROM support_portals_supportportal portal
    WHERE portal.status = 'PUBLISHED'
      AND portal.custom_domain <> ''
      AND portal.custom_domain_verified_at IS NOT NULL;
ALTER VIEW custocrm.support_portal_directory OWNER TO custocrm_schema;
REVOKE ALL ON custocrm.support_portal_directory FROM PUBLIC;
GRANT SELECT ON custocrm.support_portal_directory TO custocrm_runtime_platform;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0018_employee_groups_rls"),
        ("support_portals", "0008_remove_supportportal_department"),
    ]
    operations = [migrations.RunSQL(FORWARD_SQL, REVERSE_SQL)]
