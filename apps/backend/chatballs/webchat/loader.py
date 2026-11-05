"""Публичный автономный JS-лоадер: поля сайта, оформление, панель и анимация джина.

Модули собираются в одну IIFE; дополнительных запросов за JS на сайте нет.
"""

from pathlib import Path

_ASSETS = Path(__file__).with_name("loader_assets")
LOADER_JS = (_ASSETS / "runtime.js").read_text(encoding="utf-8")
for _module in ("site_fields", "observations", "appearance", "launcher", "site_events", "site_invitation", "genie"):
    LOADER_JS = LOADER_JS.replace(
        f"/*__{_module.upper()}__*/",
        (_ASSETS / f"{_module}.js").read_text(encoding="utf-8"),
    )
