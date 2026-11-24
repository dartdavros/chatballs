"""Демонстрационные данные для локального тестирования и установки облака.

Пакет читает редактируемые JSON-манифесты из :mod:`demo_seed.data` и через
:func:`chatballs.identity.demo_seed.orchestrator.run_demo_seed` создаёт
полный набор выдуманных данных магазина «Северный ветер». Идемпотентен:
повторный запуск не дублирует и не затирает существующие записи.
"""

__all__ = ["run_demo_seed"]


def __getattr__(name):
    if name == "run_demo_seed":
        from chatballs.identity.demo_seed.orchestrator import run_demo_seed

        return run_demo_seed
    raise AttributeError(name)
