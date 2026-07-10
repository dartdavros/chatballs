"""Static reference specs для seed_hub_initial_data.

Вынесено отдельно, чтобы management-команда оставалась компактной (NO GOD FILES):
спецификации каналов/продуктов — данные, логика наполнения — в команде.
"""

# Тон общения (поле tone агента, ADR-HUB-0023): простой текст для мессенджера.
TONE = (
    "Пиши простым текстом для мессенджера: без markdown-разметки, короткими абзацами, "
    "на русском, по делу. Не проводи оплату и не обещай условия вне базы знаний."
)

CHANNEL_SPECS = (
    {
        "code": "edevs",
        "name": "Edevs — главный сайт",
        "product_code": None,
        "department": "sales",
        "persona": "Ты — AI-ассистент компании Edevs на её главном сайте.",
        "instructions": "",
        "policy": None,  # публичный канал: дефолтные sales-флаги
    },
    {
        "code": "foxray-sales",
        "name": "FoxRay — продажи",
        "product_code": "foxray",
        "department": "sales",
        "persona": "Ты — AI sales-ассистент продукта FoxRay для ортодонтов.",
        "instructions": "",
        "policy": None,
    },
    {
        "code": "firepage-sales",
        "name": "FirePage — продажи",
        "product_code": "firepage",
        "department": "sales",
        "persona": "Ты — AI sales-ассистент продукта FirePage: готовые нишевые сайты.",
        "instructions": "",
        "policy": None,
    },
    # Support-каналы (SPEC-HUB-0010 §4.2): authenticated in-product чат,
    # anonymous/self-reported/sales/checkout запрещены.
    {
        "code": "foxray-support",
        "name": "FoxRay — поддержка",
        "product_code": "foxray",
        "department": "support",
        "persona": "Ты — AI поддержки продукта FoxRay.",
        "instructions": (
            "Помогай по использованию, учитывай verified product context. Не запрашивай"
            " имя/email, не продавай и не обещай изменения аккаунта/оплаты без оператора."
        ),
        "policy": {
            "requires_authenticated_product_identity": True,
            "allow_anonymous_sessions": False,
            "allow_self_reported_contact": False,
            "allow_sales_attribution": False,
            "allow_checkout_actions": False,
        },
    },
    {
        "code": "firepage-support",
        "name": "FirePage — поддержка",
        "product_code": "firepage",
        "department": "support",
        "persona": "Ты — AI поддержки продукта FirePage.",
        "instructions": (
            "Помогай по использованию, учитывай verified product context. Не запрашивай"
            " имя/email, не продавай и не обещай изменения аккаунта/оплаты без оператора."
        ),
        "policy": {
            "requires_authenticated_product_identity": True,
            "allow_anonymous_sessions": False,
            "allow_self_reported_contact": False,
            "allow_sales_attribution": False,
            "allow_checkout_actions": False,
        },
    },
)

PRODUCT_SPECS = (
    {
        "code": "firepage",
        "name": "FirePage",
        "site_url": "https://firepage.ru",
    },
    {
        "code": "foxray",
        "name": "FoxRay",
        "site_url": "https://foxray.pro",
    },
)
