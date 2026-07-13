from django.db import migrations


SALES_CAPABILITIES = (
    "conversations.view",
    "conversations.operate",
    "conversations.call",
    "customers.view",
    "customers.manage",
    "products.view",
    "sales.view",
    "sales.operate",
)
SUPPORT_CAPABILITIES = (
    "conversations.view",
    "conversations.operate",
    "conversations.call",
    "customers.view",
    "products.view",
    "support.view",
    "support.operate",
)
GENERIC_CAPABILITIES = (
    "conversations.view",
    "conversations.operate",
    "conversations.call",
)


def backfill_employee_access(apps, schema_editor):
    AccessProfile = apps.get_model("identity", "AccessProfile")
    AccessProfileCapability = apps.get_model("identity", "AccessProfileCapability")
    EmployeeAccessAssignment = apps.get_model("identity", "EmployeeAccessAssignment")
    EmployeeProfile = apps.get_model("identity", "EmployeeProfile")
    AuditEvent = apps.get_model("identity", "AuditEvent")

    employees = EmployeeProfile.objects.filter(role="EMPLOYEE").select_related(
        "organization", "primary_department"
    )
    for employee in employees.iterator():
        department = employee.primary_department
        # A company-level employee had no safe, unambiguous legacy department scope.
        # Deny-by-default is narrower and therefore migration-safe.
        if department is None:
            continue
        if department.code == "sales":
            name, capabilities = "Sales operator", SALES_CAPABILITIES
        elif department.code == "support":
            name, capabilities = "Support operator", SUPPORT_CAPABILITIES
        else:
            name, capabilities = "Conversation operator", GENERIC_CAPABILITIES

        profile, _ = AccessProfile.objects.get_or_create(
            organization_id=employee.organization_id,
            name=name,
            defaults={
                "description": "System profile created by authorization migration",
                "is_system": True,
                "is_active": True,
            },
        )
        for code in capabilities:
            AccessProfileCapability.objects.get_or_create(
                access_profile_id=profile.id,
                capability_code=code,
            )
        owner = EmployeeProfile.objects.filter(
            organization_id=employee.organization_id, role="OWNER"
        ).first()
        if owner is None:
            continue
        assignment, created = EmployeeAccessAssignment.objects.get_or_create(
            employee_id=employee.id,
            access_profile_id=profile.id,
            scope_type="DEPARTMENT",
            department_id=department.id,
            revoked_at__isnull=True,
            defaults={"assigned_by_id": owner.id},
        )
        if created:
            AuditEvent.objects.create(
                organization_id=employee.organization_id,
                actor_id=owner.user_id,
                action="access_assignment.created",
                object_type="EmployeeAccessAssignment",
                object_id=str(assignment.id),
                payload={"migration": True, "employeeId": employee.user_id},
            )


def noop(apps, schema_editor):
    # Access history is intentionally retained on rollback of application code.
    pass


class Migration(migrations.Migration):
    dependencies = [("identity", "0009_access_profiles_and_assignments")]
    operations = [migrations.RunPython(backfill_employee_access, noop)]
