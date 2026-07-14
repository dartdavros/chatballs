from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from hub_platform.identity.models import EmployeeProfile, EmployeeRole, Organization


class Command(BaseCommand):
    help = "Read-only verification report for the capability authorization cutover"

    def handle(self, *args, **options):
        issues: list[str] = []

        legacy_roles = EmployeeProfile.objects.filter(role="OPERATOR").count()
        if legacy_roles:
            issues.append(f"active legacy role rows: {legacy_roles}")

        missing_titles = EmployeeProfile.objects.filter(
            Q(user__is_active=True) & (Q(position_title="") | Q(position_title__isnull=True))
        ).count()
        if missing_titles:
            issues.append(f"active employees without position title: {missing_titles}")

        invalid_owner_organizations = list(
            Organization.objects.annotate(
                owner_count=Count(
                    "memberships", filter=Q(memberships__role=EmployeeRole.OWNER)
                )
            )
            .exclude(owner_count=1)
            .values_list("id", flat=True)
        )
        if invalid_owner_organizations:
            issues.append(f"organizations with invalid owner count: {invalid_owner_organizations}")

        owners_with_department = EmployeeProfile.objects.filter(
            role=EmployeeRole.OWNER, primary_department__isnull=False
        ).count()
        if owners_with_department:
            issues.append(f"owners with primary department: {owners_with_department}")

        employees_without_access = EmployeeProfile.objects.filter(
            role=EmployeeRole.EMPLOYEE,
            user__is_active=True,
        ).exclude(
            access_assignments__revoked_at__isnull=True,
            access_assignments__access_profile__is_active=True,
        )
        self.stdout.write(
            f"active employees without work assignments: {employees_without_access.count()}"
        )
        for employee in employees_without_access.select_related("user"):
            self.stdout.write(f"  - {employee.user.email}")

        if issues:
            raise CommandError("Authorization verification failed: " + "; ".join(issues))
        self.stdout.write(self.style.SUCCESS("Authorization verification passed"))
