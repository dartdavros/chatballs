from django.test import SimpleTestCase, TestCase

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.services import IntegrationInput, create_integration
from chatballs.testing import system_tenant_context
from chatballs.webchat.custom_css import sanitize_custom_css
from chatballs.webchat.launcher_css import launcher_css


class CustomCssSanitizingTests(SimpleTestCase):
    def test_launcher_css_only_exports_button_rules_and_rejects_host_resources(self):
        css = """.cb-launcher, body{border-radius:12px; background-image:image-set("https://example.org/a.png" 1x)}
        .chatballs-chat-launcher:hover > svg{color:red}
        .cb-launcher{background:url(/private);box-shadow:0 4px 8px #123}
        .cb-launcher + input{color:yellow}"""
        result = launcher_css(css)
        self.assertIn(".cb-launcher{border-radius:12px;}", result)
        self.assertIn(".chatballs-chat-launcher:hover > svg{color:red;}", result)
        self.assertIn("box-shadow:", result)
        for forbidden in ("body", "image-set", "/private", "input"):
            self.assertNotIn(forbidden, result)

    def test_import_is_cut(self) -> None:
        for css in (
            '@import "https://evil.example/x.css";',
            "@import url(https://evil.example/x.css) screen;",
            "@IMPORT 'x.css';",
            "@\\69mport 'x.css';",
        ):
            with self.subTest(css=css):
                self.assertNotIn("import", sanitize_custom_css(css + "\n.cb-header{color:red}").lower())
        self.assertIn(".cb-header{color:red}", sanitize_custom_css("@import 'x.css';\n.cb-header{color:red}"))

    def test_external_url_is_cut(self) -> None:
        for target in (
            "https://evil.example/a.png",
            "'http://evil.example/a.png'",
            '"//evil.example/a.png"',
            "javascript:alert(1)",
            '"/\t/evil.example/a.png"',
            "/\\evil.example/a.png",
            "https://evil.example/a.png",
        ):
            with self.subTest(target=target):
                css = f".cb-body{{background:url({target})}}"
                self.assertNotIn("evil", sanitize_custom_css(css))
                self.assertNotIn("javascript", sanitize_custom_css(css))
        escaped = sanitize_custom_css(".cb-body{background:\\75 rl(https://evil.example/a.png)}")
        self.assertNotIn("evil", escaped)
        unterminated = sanitize_custom_css(".cb-body{background:url(https://evil.example/a.png")
        self.assertNotIn("evil", unterminated)

    def test_local_url_is_kept(self) -> None:
        css = (
            ".a{background:url(#grad)}"
            ".b{background:url('/media/organizations/x/bg.png')}"
            ".c{background:url(data:image/png;base64,AAAA)}"
            ".d{background:url(img/bg.png)}"
        )
        self.assertEqual(sanitize_custom_css(css), css)

    def test_expression_is_cut(self) -> None:
        cleaned = sanitize_custom_css(".cb-header{width:expression(alert(1));color:red}")
        self.assertNotIn("expression", cleaned)
        self.assertIn("color:red", cleaned)
        self.assertNotIn("expression", sanitize_custom_css(".x{width:e\\78pression(alert(1))}"))

    def test_style_tag_cannot_be_closed(self) -> None:
        cleaned = sanitize_custom_css('.x{content:"</style><script>alert(1)</script>"}')
        self.assertNotIn("<", cleaned)

    def test_regular_css_is_untouched_and_sanitizing_is_stable(self) -> None:
        css = '.cb-header{background:#0d8a7e!important}\n.hover\\:x > .\\31 23{content:"\\2014"}'
        self.assertEqual(sanitize_custom_css(css), css)
        once = sanitize_custom_css('.x{content:"<"}')
        self.assertEqual(sanitize_custom_css(once), once)


class WebAppearanceApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.context = system_tenant_context(self.organization)
        self.channel = Channel.objects.create(organization=self.organization, code="site", name="Сайт")
        self.integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.WEB,
                name="Виджет",
                channel_id=self.channel.id,
                config={"allowedOrigins": ["example.com"], "accent": "#0d8a7e"},
            ),
        )
        self.client.login(username="owner@example.com", password="temporary-password")

    def _url(self) -> str:
        return f"/api/v1/organizations/{self.organization.public_id}/integrations/{self.integration.id}/"

    def _patch(self, config: dict):
        return self.client.patch(
            self._url(),
            data={"config": {"allowedOrigins": ["example.com"], **config}},
            content_type="application/json",
        )

    def _public_config(self) -> dict:
        response = self.client.get(
            "/api/v1/webchat/config/",
            {"widgetKey": self.integration.web_chat_widget.public_key},
            HTTP_ORIGIN="https://example.com",
        )
        self.assertEqual(response["Cache-Control"], "no-cache")
        return response.json()

    def test_valid_appearance_is_saved_and_published(self) -> None:
        appearance = {
            "accent": "#FFD400",
            "theme": "dark",
            "launcherIcon": "/media/organizations/x/webchat/icon.svg",
            "headerIcon": None,
            "launcherPosition": "left",
            "launcherSize": 64,
            "launcherShape": "rounded",
            "customCss": "@import 'x.css';\n.cb-header{background:url(https://evil.example/a.png);color:red}",
        }
        response = self._patch({"appearance": appearance})

        self.assertEqual(response.status_code, 200, response.content)
        saved = response.json()["integration"]["config"]
        self.assertEqual(saved["accent"], "#ffd400")
        self.assertEqual(saved["appearance"]["launcherPosition"], "left")
        self.assertEqual(saved["appearance"]["launcherSize"], 64)
        self.assertIsNone(saved["appearance"]["headerIcon"])
        self.assertEqual(saved["appearance"]["customCss"], ".cb-header{background:;color:red}")

        public = self._public_config()
        self.assertEqual(public["accent"], "#ffd400")
        self.assertEqual(
            public["appearance"],
            {
                "accent": "#ffd400",
                "theme": "dark",
                "launcherIcon": "/media/organizations/x/webchat/icon.svg",
                "headerIcon": None,
                "launcherPosition": "left",
                "launcherSize": 64,
                "launcherShape": "rounded",
                "customCss": ".cb-header{background:;color:red}",
            },
        )

    def test_invalid_appearance_is_rejected(self) -> None:
        for appearance in (
            {"accent": "blue"},
            {"accent": "#12345"},
            {"theme": "system"},
            {"launcherPosition": "top"},
            {"launcherSize": 50},
            {"launcherSize": True},
            {"launcherShape": "oval"},
            {"launcherIcon": "javascript:alert(1)"},
            {"launcherIcon": "//evil.example/icon.svg"},
            {"headerIcon": "data:image/svg+xml,<svg/>"},
            {"customCss": "a{}" * 4000},
        ):
            with self.subTest(appearance=appearance):
                response = self._patch({"appearance": appearance})
                self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(self._patch({"accent": "not-a-colour"}).status_code, 400)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.config["accent"], "#0d8a7e")

    def test_custom_css_limit_is_10_kb(self) -> None:
        exactly = "a" * (10 * 1024)
        self.assertEqual(self._patch({"appearance": {"customCss": exactly}}).status_code, 200)
        self.assertEqual(self._patch({"appearance": {"customCss": exactly + "a"}}).status_code, 400)

    def test_legacy_accent_keeps_working(self) -> None:
        # Виджет, сохранённый до appearance: цвет только в config.accent.
        Integration.objects.filter(id=self.integration.id).update(
            config={"allowed_domains": ["example.com"], "accent": "#be123c"}
        )
        widget = self.integration.web_chat_widget
        widget.presentation_config = {"accent": "#be123c"}
        widget.save(update_fields=["presentation_config"])

        public = self._public_config()
        self.assertEqual(public["accent"], "#be123c")
        self.assertEqual(public["appearance"]["accent"], "#be123c")
        self.assertEqual(public["appearance"]["launcherPosition"], "right")
        self.assertEqual(public["appearance"]["launcherSize"], 56)
        self.assertEqual(public["appearance"]["launcherShape"], "circle")

        # Прежняя форма шлёт config без appearance: оформление не сбрасывается.
        self._patch({"appearance": {"launcherPosition": "left", "headerIcon": "https://cdn.example/h.png"}})
        response = self._patch({"accent": "#4f46e5", "title": "Поддержка"})
        self.assertEqual(response.status_code, 200, response.content)
        public = self._public_config()
        self.assertEqual(public["accent"], "#4f46e5")
        self.assertEqual(public["appearance"]["launcherPosition"], "left")
        self.assertEqual(public["appearance"]["headerIcon"], "https://cdn.example/h.png")

    def test_header_icon_defaults_to_launcher_icon(self) -> None:
        self._patch({"appearance": {"launcherIcon": "https://cdn.example/l.svg"}})
        public = self._public_config()
        self.assertEqual(public["appearance"]["headerIcon"], "https://cdn.example/l.svg")

    def test_icons_can_be_reset_and_header_icon_removed(self) -> None:
        # «Сбросить» шлёт пустую строку, «Без иконки» — null (SPEC-0021 R-12).
        own = {
            "launcherIcon": "https://cdn.example/l.svg",
            "headerIcon": "https://cdn.example/h.png",
        }
        self._patch({"appearance": own})

        response = self._patch({"appearance": {**own, "headerIcon": None}})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["integration"]["config"]["appearance"]["headerIcon"])
        self.assertIsNone(self._public_config()["appearance"]["headerIcon"])

        response = self._patch({"appearance": {"launcherIcon": "", "headerIcon": ""}})
        self.assertEqual(response.status_code, 200, response.content)
        saved = response.json()["integration"]["config"]["appearance"]
        self.assertEqual((saved["launcherIcon"], saved["headerIcon"]), ("", ""))
        public = self._public_config()["appearance"]
        self.assertEqual((public["launcherIcon"], public["headerIcon"]), ("", ""))

    def test_loader_is_cached_no_longer_than_five_minutes(self) -> None:
        response = self.client.get("/chat-widget.js")
        self.assertEqual(response["Cache-Control"], "public, max-age=300")

    def test_allowed_site_can_read_public_config_without_credentials(self) -> None:
        response = self.client.get(
            "/api/v1/webchat/config/",
            {"widgetKey": self.integration.web_chat_widget.public_key},
            HTTP_ORIGIN="https://example.com",
        )
        self.assertTrue(response.json()["available"])
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://example.com")
        self.assertFalse(response.has_header("Access-Control-Allow-Credentials"))
        self.assertIn("Origin", response["Vary"])

    def test_other_site_cannot_override_origin_or_read_config(self) -> None:
        response = self.client.get(
            "/api/v1/webchat/config/",
            {
                "widgetKey": self.integration.web_chat_widget.public_key,
                "hostOrigin": "https://example.com",
            },
            HTTP_ORIGIN="https://other.example",
        )
        self.assertFalse(response.json()["available"])
        self.assertFalse(response.has_header("Access-Control-Allow-Origin"))

    def test_loader_host_origin_and_legacy_channel_are_supported(self) -> None:
        response = self.client.get(
            "/api/v1/webchat/config/",
            {"channel": self.channel.code, "hostOrigin": "https://example.com"},
        )
        self.assertTrue(response.json()["available"])
        self.assertEqual(response.json()["widgetKey"], self.integration.web_chat_widget.public_key)
