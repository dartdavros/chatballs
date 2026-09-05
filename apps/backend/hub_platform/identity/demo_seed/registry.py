"""Реестр созданных сидом записей и их точное удаление.

Запись: на время установки к ``post_save`` подключается приёмник, который
регистрирует каждую созданную (``created=True``) запись любой модели в
``DemoRecord`` с порядковым номером. Сид создаёт данные через сервисы
системы, поэтому реестр покрывает и побочные записи (аудит, уведомления,
фрагменты знаний, сессии веб-чата).

Удаление: записи удаляются по одной в порядке, обратном созданию — так
зависимые строки уходят раньше родителей, а PROTECT-связи не мешают.
Каскадно удалённые ранее строки просто пропускаются. Файлы FileField
удаляются из хранилища вместе с записью.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from django.db.models.signals import post_save

from hub_platform.identity.demo_models import DemoDataset, DemoRecord

logger = logging.getLogger(__name__)

# Модели, которые реестр не регистрирует: сам реестр и типы контента.
_IGNORED_MODELS = {DemoDataset, DemoRecord, ContentType}


class DemoRecorder:
    """Собирает созданные записи в ``DemoRecord`` дата-сета."""

    def __init__(self, dataset: DemoDataset) -> None:
        self.dataset = dataset
        self.sequence = (
            DemoRecord.objects.filter(dataset=dataset).order_by("-sequence")
            .values_list("sequence", flat=True)
            .first()
            or 0
        )
        self._content_types: dict[type[models.Model], ContentType] = {}

    def _content_type(self, model: type[models.Model]) -> ContentType:
        cached = self._content_types.get(model)
        if cached is None:
            cached = ContentType.objects.get_for_model(model, for_concrete_model=True)
            self._content_types[model] = cached
        return cached

    def on_post_save(self, sender, instance, created, raw=False, **kwargs) -> None:  # noqa: ANN001
        if not created or raw or sender in _IGNORED_MODELS or sender._meta.abstract:
            return
        if sender._meta.app_label == "sessions":
            return
        self.sequence += 1
        DemoRecord.objects.create(
            organization_id=self.dataset.organization_id,
            dataset=self.dataset,
            content_type=self._content_type(sender),
            object_id=str(instance.pk),
            sequence=self.sequence,
        )

    def record(self, instance: models.Model) -> None:
        """Явная регистрация записи, созданной без сигнала (bulk_create)."""
        self.on_post_save(type(instance), instance, True)


@contextmanager
def recording(dataset: DemoDataset) -> Iterator[DemoRecorder]:
    recorder = DemoRecorder(dataset)
    post_save.connect(recorder.on_post_save, dispatch_uid=f"demo-recorder-{dataset.pk}", weak=False)
    try:
        yield recorder
    finally:
        post_save.disconnect(dispatch_uid=f"demo-recorder-{dataset.pk}")


def _delete_files(instance: models.Model) -> None:
    for field in instance._meta.get_fields():
        if isinstance(field, models.FileField):
            file = getattr(instance, field.name, None)
            if file and file.name:
                try:
                    file.delete(save=False)
                except Exception:  # noqa: BLE001 — файл не должен блокировать удаление записи
                    logger.warning("Demo file %s was not deleted", file.name, exc_info=True)


def _detach_demo_references(instance: models.Model, demo_keys: set[tuple[int, str]]) -> bool:
    """Обнуляет nullable-FK записи на другие демо-объекты — разрывает циклы
    PROTECT (статья ↔ опубликованная ревизия). Только демо-объекты: реальные
    данные не трогаются. Возвращает ``True``, если что-то обнулено."""
    updates: dict[str, None] = {}
    for field in instance._meta.get_fields():
        if not isinstance(field, models.ForeignKey) or not field.null:
            continue
        target_id = getattr(instance, field.attname)
        if target_id is None:
            continue
        target_ct = ContentType.objects.get_for_model(field.remote_field.model, for_concrete_model=True)
        if (target_ct.id, str(target_id)) in demo_keys:
            updates[field.attname] = None
    if not updates:
        return False
    type(instance)._base_manager.filter(pk=instance.pk).update(**updates)
    return True


def _delete_record(record: DemoRecord, demo_keys: set[tuple[int, str]]) -> bool:
    """Удаляет запись реестра и её объект. ``False`` — объект защищён
    (PROTECT) ещё живой записью; попытка повторяется позже."""
    model = record.content_type.model_class()
    if model is None:
        record.delete()
        return True
    instance = model._base_manager.filter(pk=record.object_id).first()
    if instance is None:
        record.delete()
        return True
    for attempt in range(2):
        try:
            with transaction.atomic():
                _delete_files(instance)
                instance.delete()
            break
        except ProtectedError:
            if attempt == 1 or not _detach_demo_references(instance, demo_keys):
                return False
            instance = model._base_manager.get(pk=record.object_id)
    record.delete()
    return True


def remove_records(dataset: DemoDataset) -> int:
    """Удаляет все записи дата-сета в обратном порядке создания.

    Обратный порядок снимает почти все зависимости; оставшиеся защищённые
    связи (например, статья портала ↔ её опубликованная ревизия) разрешаются
    повторными проходами: после удаления родителя каскад забирает зависимую
    запись, и на следующем проходе она уже отсутствует.
    """
    removed = 0
    pending = list(dataset.records.select_related("content_type").order_by("-sequence"))
    demo_keys = {(record.content_type_id, record.object_id) for record in pending}
    while pending:
        deferred: list[DemoRecord] = []
        for record in pending:
            existed = record.content_type.model_class() is not None and (
                record.content_type.model_class()._base_manager.filter(pk=record.object_id).exists()
            )
            if _delete_record(record, demo_keys):
                removed += int(existed)
            else:
                deferred.append(record)
        if len(deferred) == len(pending):
            blocked = ", ".join(f"{r.content_type.model}:{r.object_id}" for r in deferred[:5])
            raise ProtectedError(f"Demo records cannot be deleted: {blocked}", set())
        pending = deferred
    return removed
