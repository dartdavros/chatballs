from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from hub_platform.identity.models import Organization
from hub_platform.subscriptions.models import Subscription
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.tenancy.database import set_local_tenant


class SubscriptionRowLevelSecurityTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.first = Organization.objects.create(name="RLS first", slug="subscription-rls-first")
        self.second = Organization.objects.create(name="RLS second", slug="subscription-rls-second")
        create_test_subscription(self.first, quantity=1)
        create_test_subscription(self.second, quantity=1)

    @staticmethod
    def _set_role(role: str = "custocrm_runtime_app") -> None:
        if role not in {"custocrm_runtime_app", "custocrm_runtime_platform"}:
            raise ValueError("Unexpected runtime role")
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {role}")

    def test_runtime_role_is_fail_closed_and_tenant_scoped(self) -> None:
        with transaction.atomic():
            self._set_role()
            self.assertEqual(Subscription.objects.count(), 0)
        with transaction.atomic():
            self._set_role()
            set_local_tenant(self.first.id)
            self.assertEqual(
                list(Subscription.objects.values_list("organization_id", flat=True)),
                [self.first.id],
            )
        with transaction.atomic():
            self._set_role("custocrm_runtime_platform")
            set_local_tenant(self.second.id)
            self.assertEqual(
                list(Subscription.objects.values_list("organization_id", flat=True)),
                [self.second.id],
            )
        with self.assertRaises(DatabaseError), transaction.atomic():
            self._set_role()
            set_local_tenant(self.first.id)
            own = Subscription.objects.get(organization_id=self.first.id)
            own.organization_id = self.second.id
            own.save(update_fields=["organization_id"])
