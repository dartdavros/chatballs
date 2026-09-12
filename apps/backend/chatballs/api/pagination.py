"""Единый контракт постраничных и оконных ответов API.

Режима два, и оба серверные — ни один список не отдаётся целиком:

* **Страницы** (`paginate`) — списки с номерами страниц в интерфейсе: порталы,
  библиотека статей, контакты, сотрудники, агенты. Ответ несёт `page`,
  `pageSize`, `total`, `pageCount`, поэтому подвал со страницами рисуется без
  догадок о размере набора.
* **Окно по курсору** (`window`) — живые ленты: список диалогов и история
  сообщений. Номера страниц там бессмысленны: новая запись приходит сверху и
  сдвигает нумерацию, из-за чего offset выдаёт дубли и пропуски. Курсор —
  идентификатор граничной записи; сравнение строится по тому же порядку
  сортировки, что и сам список (keyset pagination).

Оба режима отдают на один элемент больше запрошенного только внутри окна —
наружу уходит ровно `limit`, а лишний элемент превращается в `hasMore`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError

from chatballs.i18n import t

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_WINDOW_SIZE = 50
MAX_WINDOW_SIZE = 200
# Верхняя граница номера страницы: защита от `?page=99999999`, где OFFSET
# заставит базу пройти весь индекс ради пустого ответа.
MAX_PAGE_NUMBER = 100_000


def _bounded_int(params, name: str, default: int, maximum: int) -> int:
    raw = params.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(t("api.expected_integer", name=name)) from None
    if value < 1:
        raise ValidationError(t("api.expected_positive", name=name))
    return min(value, maximum)


def cursor_id(params, name: str = "cursor") -> int | None:
    """Курсор окна — id граничной записи. Пустой параметр означает начало ленты."""
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(t("api.expected_record_id", name=name)) from None
    if value < 1:
        raise ValidationError(t("api.expected_record_id", name=name))
    return value


@dataclass(frozen=True)
class Page:
    """Одна страница набора: сами записи и всё, что нужно подвалу со страницами."""

    items: list[Any]
    page: int
    page_size: int
    total: int

    @property
    def page_count(self) -> int:
        return max(1, -(-self.total // self.page_size))


def paginate(
    queryset: QuerySet,
    params,
    *,
    default_size: int = DEFAULT_PAGE_SIZE,
    max_size: int = MAX_PAGE_SIZE,
) -> Page:
    """Страница набора по `?page=&pageSize=`.

    Запрос страницы за пределами набора возвращает последнюю существующую: так
    список не становится пустым, когда записи удалили из-под открытой страницы.
    """
    page_size = _bounded_int(params, "pageSize", default_size, max_size)
    requested = _bounded_int(params, "page", 1, MAX_PAGE_NUMBER)
    total = queryset.count()
    page_count = max(1, -(-total // page_size))
    page = min(requested, page_count)
    start = (page - 1) * page_size
    return Page(
        items=list(queryset[start : start + page_size]),
        page=page,
        page_size=page_size,
        total=total,
    )


def page_payload(page: Page, serialize: Callable[[Any], dict]) -> dict[str, object]:
    return {
        "items": [serialize(item) for item in page.items],
        "page": page.page,
        "pageSize": page.page_size,
        "total": page.total,
        "pageCount": page.page_count,
    }


@dataclass(frozen=True)
class SortKey:
    """Поле сортировки окна: имя поля или annotation и направление.

    Поле обязано быть непустым (NOT NULL или Coalesce): сравнение курсора по
    NULL в SQL не даёт истины, и окно молча теряло бы записи.
    """

    field: str
    descending: bool = True

    @property
    def ordering(self) -> str:
        return f"-{self.field}" if self.descending else self.field

    @property
    def lookup(self) -> str:
        return f"{self.field}__{'lt' if self.descending else 'gt'}"


@dataclass(frozen=True)
class Window:
    """Окно ленты: записи в порядке сортировки и курсор на продолжение."""

    items: list[Any]
    has_more: bool

    @property
    def cursor(self) -> int | None:
        return self.items[-1].pk if self.items and self.has_more else None


def window_payload(
    win: Window, serialize: Callable[[Any], dict], *, total: int | None = None
) -> dict[str, object]:
    """Тело ответа-окна. `total` добавляется там, где интерфейс показывает
    размер всего набора (счётчик над списком), и стоит одного COUNT."""
    payload: dict[str, object] = {
        "items": [serialize(item) for item in win.items],
        "hasMore": win.has_more,
        "cursor": win.cursor,
    }
    if total is not None:
        payload["total"] = total
    return payload


def _after_cursor(queryset: QuerySet, keys: Sequence[SortKey], anchor_id: int) -> Q | None:
    """Условие «строго после записи anchor_id» в порядке keys.

    Значения ключей берутся из того же queryset, поэтому annotation-поля
    (например, время последнего сообщения) доступны наравне с обычными.
    """
    fields = [key.field for key in keys]
    anchor = queryset.filter(pk=anchor_id).values(*fields).first()
    if anchor is None:
        # Курсор указывает на запись, которой в наборе больше нет (её удалили,
        # закрыли или она ушла под фильтр). Отдать начало ленты вместо пустоты.
        return None
    condition = Q()
    equal_prefix = Q()
    for key in keys:
        condition |= equal_prefix & Q(**{key.lookup: anchor[key.field]})
        equal_prefix &= Q(**{key.field: anchor[key.field]})
    return condition


def window(
    queryset: QuerySet,
    *,
    keys: Sequence[SortKey],
    limit: int,
    after: int | None = None,
) -> Window:
    """Окно записей по курсору.

    `keys` задаёт и порядок, и правило сравнения; последним ключом должен идти
    уникальный столбец (обычно `id`), иначе записи с одинаковым временем будут
    выпадать из ленты или повторяться на границе окна.
    """
    if not keys:
        raise ValueError(t("api.window_needs_sort_key"))
    ordered = queryset.order_by(*[key.ordering for key in keys])
    if after is not None:
        condition = _after_cursor(ordered, keys, after)
        if condition is not None:
            ordered = ordered.filter(condition)
    items = list(ordered[: limit + 1])
    has_more = len(items) > limit
    return Window(items=items[:limit], has_more=has_more)


def window_size(params, *, default: int = DEFAULT_WINDOW_SIZE, name: str = "limit") -> int:
    return _bounded_int(params, name, default, MAX_WINDOW_SIZE)
