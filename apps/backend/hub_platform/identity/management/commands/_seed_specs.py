"""Static reference specs для seed_hub_initial_data.

Вынесено отдельно, чтобы management-команда оставалась компактной (NO GOD FILES):
спецификации каналов/продуктов — данные, логика наполнения — в команде.
"""

STYLE = (
    " Пиши простым текстом для мессенджера: без markdown-разметки, короткими абзацами, "
    "на русском, по делу. Не проводи оплату и не обещай условия вне базы знаний."
)

CHANNEL_SPECS = (
    {
        "code": "edevs",
        "name": "Edevs — главный сайт",
        "product_code": None,
        "department": "sales",
        "system_prompt": "Ты — AI-ассистент компании Edevs на её главном сайте." + STYLE,
        "policy": None,  # публичный канал: дефолтные sales-флаги
    },
    {
        "code": "foxray-sales",
        "name": "FoxRay — продажи",
        "product_code": "foxray",
        "department": "sales",
        "system_prompt": "Ты — AI sales-ассистент продукта FoxRay для ортодонтов." + STYLE,
        "policy": None,
    },
    {
        "code": "firepage-sales",
        "name": "FirePage — продажи",
        "product_code": "firepage",
        "department": "sales",
        "system_prompt": (
            "Ты — AI sales-ассистент продукта FirePage: готовые нишевые сайты." + STYLE
        ),
        "policy": None,
    },
    # Support-каналы (SPEC-HUB-0010 §4.2): authenticated in-product чат,
    # anonymous/self-reported/sales/checkout запрещены.
    {
        "code": "foxray-support",
        "name": "FoxRay — поддержка",
        "product_code": "foxray",
        "department": "support",
        "system_prompt": (
            "Ты — AI поддержки продукта FoxRay. Помогай по использованию, учитывай"
            " verified product context. Не запрашивай имя/email, не продавай и не"
            " обещай изменения аккаунта/оплаты без оператора." + STYLE
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
        "system_prompt": (
            "Ты — AI поддержки продукта FirePage. Помогай по использованию, учитывай"
            " verified product context. Не запрашивай имя/email, не продавай и не"
            " обещай изменения аккаунта/оплаты без оператора." + STYLE
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
        "summary": "Готовые нишевые сайты на собственной CMS с разовой лицензией.",
    },
    {
        "code": "foxray",
        "name": "FoxRay",
        "site_url": "https://foxray.pro",
        "summary": "Онлайн-сервис для цефалометрического анализа ТРГ.",
    },
)
