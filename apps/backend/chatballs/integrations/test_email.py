"""Email-подключение: конфигурация, проверка и сериализация (SPEC-CHATBALLS-0025 §5)."""



from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations import checks
from chatballs.integrations.models import IntegrationKind, IntegrationProvider, IntegrationStatus
from chatballs.integrations.serializers import integration_payload
from chatballs.integrations.services import IntegrationInput, create_integration
from chatballs.testing import system_tenant_context

EMAIL_INPUT = {

    "email": "Support@example.com",

    "imapHost": "imap.yandex.ru",

    "smtpHost": "smtp.yandex.ru",

}





class EmailConfigTests(TestCase):

    def setUp(self) -> None:

        bootstrap_owner(email="owner@example.com", password="temporary-password")

        self.context = system_tenant_context(Organization.objects.get(slug="demo"))



    def _create(self, *, secret="app-password", config=None):

        return create_integration(

            context=self.context,

            data=IntegrationInput(provider=IntegrationProvider.EMAIL, name="Почта", secret=secret, config=config or dict(EMAIL_INPUT)),

        )



    def test_email_is_messenger_kind_with_normalized_config(self) -> None:

        integration = self._create()

        self.assertEqual(integration.kind, IntegrationKind.MESSENGER)

        # camelCase → snake_case, адрес приводится к lowercase, порты/SSL по умолчанию.

        self.assertEqual(

            integration.config,

            {

                "email": "support@example.com",

                "imap_host": "imap.yandex.ru",

                "imap_port": 993,

                "imap_ssl": True,

                "smtp_host": "smtp.yandex.ru",

                "smtp_port": 465,

                "smtp_ssl": True,

            },

        )



    def test_secret_required_on_create(self) -> None:

        with self.assertRaises(ValidationError):

            self._create(secret="")



    def test_hosts_and_address_required(self) -> None:

        with self.assertRaises(ValidationError):

            self._create(config={"email": "a@b.c", "imapHost": "imap.b.c"})



    def test_notifications_purpose_rejected(self) -> None:

        # Email не может быть сервисным ботом уведомлений (ADR-CHATBALLS-0035, границы).

        with self.assertRaises(ValidationError):

            self._create(config={**EMAIL_INPUT, "purpose": "notifications"})



    def test_serializer_exposes_email_config(self) -> None:

        payload = integration_payload(self._create())

        config = payload["config"]

        self.assertEqual(config["email"], "support@example.com")

        self.assertEqual(config["imapHost"], "imap.yandex.ru")

        self.assertEqual(config["imapPort"], 993)

        self.assertTrue(config["smtpSsl"])

        self.assertTrue(payload["hasSecret"])





class EmailCheckTests(TestCase):

    """check_email: успех только когда успешны ОБЕ стороны (IMAP и SMTP)."""



    CONFIG = {

        "email": "support@example.com",

        "imap_host": "imap.test",

        "imap_port": 993,

        "imap_ssl": True,

        "smtp_host": "smtp.test",

        "smtp_port": 465,

        "smtp_ssl": True,

    }



    def test_both_sides_ok(self) -> None:

        with (

            mock.patch.object(checks.imaplib, "IMAP4_SSL") as imap_cls,

            mock.patch.object(checks.smtplib, "SMTP_SSL") as smtp_cls,

        ):

            ok, detail, meta = checks.check_email(secret="pw", config=self.CONFIG)

        self.assertTrue(ok)

        self.assertEqual(detail, "Email: support@example.com")

        imap_cls.return_value.login.assert_called_once_with("support@example.com", "pw")

        smtp_cls.return_value.login.assert_called_once_with("support@example.com", "pw")



    def test_imap_failure_reported(self) -> None:

        with mock.patch.object(checks.imaplib, "IMAP4_SSL", side_effect=OSError("connection refused")):

            ok, detail, _ = checks.check_email(secret="pw", config=self.CONFIG)

        self.assertFalse(ok)

        self.assertIn("IMAP:", detail)



    def test_smtp_failure_reported(self) -> None:

        with (

            mock.patch.object(checks.imaplib, "IMAP4_SSL"),

            mock.patch.object(checks.smtplib, "SMTP_SSL", side_effect=OSError("connection refused")),

        ):

            ok, detail, _ = checks.check_email(secret="pw", config=self.CONFIG)

        self.assertFalse(ok)

        self.assertIn("SMTP:", detail)



    def test_missing_secret_fails(self) -> None:

        ok, detail, _ = checks.check_email(secret="", config=self.CONFIG)

        self.assertFalse(ok)

        self.assertIn("пароль", detail)





class EmailTestIntegrationDispatchTests(TestCase):

    """test_integration диспетчеризует EMAIL на check_email (полный config)."""



    def setUp(self) -> None:

        bootstrap_owner(email="owner@example.com", password="temporary-password")

        self.context = system_tenant_context(Organization.objects.get(slug="demo"))



    def test_email_check_updates_status(self) -> None:

        from chatballs.integrations.services import test_integration as run_integration_test



        integration = create_integration(

            context=self.context,

            data=IntegrationInput(provider=IntegrationProvider.EMAIL, name="Почта", secret="pw", config=dict(EMAIL_INPUT)),

        )

        with mock.patch.object(checks, "check_email", return_value=(True, "Email: support@example.com", {})) as check:

            checked = run_integration_test(context=self.context, integration=integration)

        check.assert_called_once()

        self.assertEqual(checked.status, IntegrationStatus.OK)

        self.assertEqual(checked.last_error, "")

