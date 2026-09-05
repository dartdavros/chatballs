"""SPEC-HUB-0027 §12 — приведение данных перед включением инвариантов P1-P5.



Схема между `channels.0004` и `channels.0005` не меняется: `AlterField` правит

только Python-дефолты. Весь риск миграции сосредоточен в функции приведения

данных, поэтому она проверяется напрямую на реальном реестре моделей — это

честнее, чем поднимать историческое состояние, где `identity` откатывается

рассинхронно со схемой БД.

"""



import importlib



from django.apps import apps

from django.test import TestCase



from chatballs.channels.models import Channel

from chatballs.identity.models import Organization

from chatballs.products.models import Product



migration = importlib.import_module(

    "chatballs.channels.migrations.0005_enforce_policy_invariants"

)





class PolicyInvariantMigrationTests(TestCase):

    def setUp(self) -> None:

        self.organization = Organization.objects.create(name="Acme", slug="acme")

        self.product = Product.objects.create(

            organization=self.organization, code="app", name="FoxRay"

        )



    def _channel(self, code: str, **fields) -> Channel:

        return Channel.objects.create(

            organization=self.organization, code=code, name=code, **fields

        )



    def _run(self) -> None:

        migration.relax_non_product_channels(apps, None)



    def test_clears_commercial_flags_on_non_product_channels(self) -> None:

        # Ровно случай канала acme: непродуктовый, но с checkout и attribution.

        violating = self._channel(

            "acme", allow_checkout_actions=True, allow_sales_attribution=True

        )



        self._run()



        violating.refresh_from_db()

        self.assertFalse(violating.allow_checkout_actions)

        self.assertFalse(violating.allow_sales_attribution)

        # Остальные флаги непродуктового канала не трогаются.

        self.assertTrue(violating.allow_anonymous_sessions)

        self.assertTrue(violating.allow_self_reported_contact)



    def test_leaves_product_channels_untouched(self) -> None:

        product_channel = self._channel(

            "app-sales",

            product=self.product,

            allow_checkout_actions=True,

            allow_sales_attribution=True,

        )



        self._run()



        product_channel.refresh_from_db()

        self.assertTrue(product_channel.allow_checkout_actions)

        self.assertTrue(product_channel.allow_sales_attribution)



    def test_stops_the_rollout_on_p3_p5_violations(self) -> None:

        # Обязательная идентичность без продукта — смена смысла канала,

        # выбирать за владельца нельзя, поэтому выкат останавливается.

        self._channel("broken", requires_authenticated_product_identity=True)

        untouched = self._channel(

            "acme", allow_checkout_actions=True, allow_sales_attribution=True

        )



        with self.assertRaises(RuntimeError) as error:

            self._run()



        self.assertIn("broken", str(error.exception))

        untouched.refresh_from_db()

        self.assertTrue(untouched.allow_checkout_actions)



    def test_is_idempotent(self) -> None:

        self._channel("acme", allow_checkout_actions=True)



        self._run()

        self._run()



        self.assertEqual(

            Channel.objects.filter(

                product__isnull=True, allow_checkout_actions=True

            ).count(),

            0,

        )

