"""Демонстрационные данные для локального тестирования и установки облака.

Пакет читает редактируемые JSON-манифесты из :mod:`demo_seed.data` и через
:func:`chatballs.identity.demo_seed.orchestrator.run_demo_seed` создаёт
полный набор выдуманных данных организации «Северная Верфь». Идемпотентен:
повторный запуск не дублирует и не затирает существующие записи.
"""

from chatballs.identity.demo_seed.orchestrator import run_demo_seed

__all__ = ["run_demo_seed"]
