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
from contextvars import ContextVar
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import ProtectedError
from django.db.models.signals import post_save

from chatballs.ai.external_agents.file_models import ExternalAgentFile
from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.models import Conversation
from chatballs.conversations.quality.models import QualityCriteriaVersion, QualityJob, QualityResult
from chatballs.identity.demo_models import DemoDataset, DemoRecord
from chatballs.identity.demo_seed.conflicts import assert_demo_references
from chatballs.identity.demo_seed.north_wind.executor_artifacts import release_executor_upload
from chatballs.identity.demo_seed.waiting_notices import register_waiting_notices
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.assets import discard_widget_asset_files
from chatballs.webchat.models import WidgetAsset

logger = logging.getLogger(__name__)

# Модели, которые реестр не регистрирует: сам реестр и типы контента.
_IGNORED_MODELS = {DemoDataset, DemoRecord, ContentType}
_IMMUTABLE_MODELS = {ConversationComment, ConversationEvent, QualityCriteriaVersion, QualityResult}
_active_recorder: ContextVar[DemoRecorder | None] = ContextVar("demo_recorder", default=None)


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
        self._created: set[tuple[type[models.Model], object]] = set()
        self._files: set[tuple[object, str]] = set()

    def _content_type(self, model: type[models.Model]) -> ContentType:
        cached = self._content_types.get(model)
        if cached is None:
            cached = ContentType.objects.get_for_model(model, for_concrete_model=True)
            self._content_types[model] = cached
        return cached

    def on_post_save(self, sender, instance, created, raw=False, **kwargs) -> None:  # noqa: ANN001
        if _active_recorder.get() is not self or raw or sender in _IGNORED_MODELS or sender._meta.abstract:
            return
        if sender._meta.app_label == "sessions":
            return
        key = (sender, instance.pk)
        if created:
            self._created.add(key)
        if key in self._created:
            self._files.update(_stored_files(instance))
        if not created:
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

    def record_existing(self, instance: models.Model) -> None:
        content_type = self._content_type(type(instance))
        if not self.dataset.records.filter(content_type=content_type, object_id=str(instance.pk)).exists():
            self.record(instance)

    def protect_conversation(self, conversation: models.Model) -> None:
        self.dataset.records.filter(
            organization_id=self.dataset.organization_id,
            content_type=self._content_type(type(conversation)),
            object_id=str(conversation.pk),
        ).update(protect_from_inactivity=True)

    def discard_new_files(self) -> None:
        _delete_storage_files(self.dataset.organization_id, self._files)


@contextmanager
def recording(dataset: DemoDataset) -> Iterator[DemoRecorder]:
    recorder = DemoRecorder(dataset)
    token = _active_recorder.set(recorder)
    signal_uid = ("demo-recorder", id(recorder))
    post_save.connect(recorder.on_post_save, dispatch_uid=signal_uid, weak=False)
    try:
        yield recorder
    finally:
        post_save.disconnect(dispatch_uid=signal_uid)
        _active_recorder.reset(token)


@contextmanager
def runtime_recording(dataset):
    """Use the generation lock held by the caller to serialize registry writes."""
    existing = _active_recorder.get()
    if existing is not None and existing.dataset.pk == dataset.pk:
        yield existing
        return
    recorder = None
    try:
        with transaction.atomic(), recording(dataset) as recorder:
            before = recorder.sequence
            yield recorder
            if recorder.sequence != before:
                dataset.records_count = dataset.records.count()
                dataset.save(update_fields=["records_count"])
    except Exception:
        if recorder is not None:
            recorder.discard_new_files()
        raise


def _stored_files(instance):
    for field in instance._meta.get_fields():
        if isinstance(field, models.FileField):
            file = getattr(instance, field.name, None)
            if file and file.name and file._committed:
                yield file.storage, file.name


def _delete_storage_files(organization_id, files):
    if not files:
        return
    with tenant_atomic(organization_id):
        for storage, name in files:
            try:
                storage.delete(name)
            except Exception:  # noqa: BLE001
                logger.warning("Demo file %s was not deleted", name, exc_info=True)


def _delete_files(instance: models.Model, organization_id: int) -> None:
    if isinstance(instance, WidgetAsset):
        discard_widget_asset_files(
            context=TenantContext.for_resource(instance.organization),
            files=[(instance.file.name, instance.size)] if instance.file.name else [],
        )
        return
    if isinstance(instance, ExternalAgentFile) and not release_executor_upload(instance):
        return
    files = list(_stored_files(instance))
    if files:
        transaction.on_commit(partial(_delete_storage_files, organization_id, files), robust=True)


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
    (PROTECT) ещё живой записью; попытка повторяется позже.

    Зависимые записи удаляются по реестру. Для циклов допускается обнуление
    связей только между записями набора."""
    model = record.content_type.model_class()
    if model is None:
        record.delete()
        return True
    instance = model._base_manager.filter(pk=record.object_id).first()
    if instance is None:
        record.delete()
        return True
    if model in {ConversationComment, QualityJob, QualityResult}:
        conversation_id = instance.job.conversation_id if model is QualityResult else instance.conversation_id
        parent_type = ContentType.objects.get_for_model(Conversation)
        if (parent_type.pk, str(conversation_id)) not in demo_keys:
            return False
        # The database removes append-only comments and quality evidence
        # through the owned conversation's deletion.
        record.delete()
        return True
    for attempt in range(2):
        try:
            with transaction.atomic():
                _delete_files(instance, record.organization_id)
                instance.delete()
            break
        except ProtectedError as error:
            if attempt:
                return False
            try:
                with transaction.atomic():
                    detached = _detach_demo_references(instance, demo_keys)
                    for dependent in error.protected_objects:
                        content_type = ContentType.objects.get_for_model(type(dependent))
                        if (content_type.id, str(dependent.pk)) in demo_keys:
                            detached |= _detach_demo_references(dependent, demo_keys)
                    if not detached:
                        return False
            except IntegrityError:
                return False
    record.delete()
    return True


def remove_records(dataset: DemoDataset) -> int:
    """Удаляет все записи дата-сета в обратном порядке создания.

    Обратный порядок снимает почти все зависимости; оставшиеся защищённые
    связи (например, статья портала ↔ её опубликованная ревизия) разрешаются
    повторными проходами: после удаления родителя каскад забирает зависимую
    запись, и на следующем проходе она уже отсутствует.
    """
    from chatballs.identity.demo_seed.north_wind.delivery_artifacts import register_delivery_runs
    from chatballs.identity.demo_seed.north_wind.executor_artifacts import (
        purge_demo_template_versions,
        register_executor_artifacts,
    )
    from chatballs.identity.demo_seed.north_wind.support_artifacts import register_thread_history

    register_delivery_runs(dataset)
    register_executor_artifacts(dataset)
    register_waiting_notices(dataset)
    register_thread_history(dataset)
    removed = 0
    pending = list(dataset.records.select_related("content_type").order_by("-sequence"))
    demo_keys = {(record.content_type_id, record.object_id) for record in pending}
    owned = {}
    for record in pending:
        model = record.content_type.model_class()
        if model is not None:
            owned.setdefault(model, set()).add(record.object_id)
    for model, ids in owned.items():
        records = model._base_manager.filter(pk__in=ids)
        # PostgreSQL requires UPDATE for row locking. These records are
        # append-only, and their owned conversation is already locked.
        if model not in _IMMUTABLE_MODELS:
            records = records.select_for_update()
        for instance in records:
            assert_demo_references(instance, owned, dataset)
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
    purge_demo_template_versions(dataset)
    return removed
