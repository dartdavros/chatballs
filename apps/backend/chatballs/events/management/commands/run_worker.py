import logging
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatballs.calls.maintenance import expire_stale_calls
from chatballs.conversations.maintenance import close_stale_conversations
from chatballs.conversations.poller import poll_all_messengers
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxStatus
from chatballs.events.services import claim_next_outbox_event, mark_retry
from chatballs.notifications.binding import poll_notifier_bots
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import iter_organizations
from chatballs.updates.services import check_for_updates

logger = logging.getLogger(__name__)

MESSENGER_POLL_INTERVAL = 3.0  # seconds between messenger long-poll cycles
MAINTENANCE_INTERVAL = 3600.0  # seconds between maintenance cycles (auto-close stale dialogs)
CALL_SWEEP_INTERVAL = 10.0  # seconds between call timeout sweeps (invite expiry, stuck connect)


class Command(BaseCommand):
    help = "Runs the local domain event worker (outbox dispatch + messenger inbound polling)."

    @staticmethod
    def _tenant_contexts():
        for organization in iter_organizations():
            yield TenantContext.for_resource(
                organization, actor_kind=TenantActorKind.SYSTEM
            )

    def handle(self, *args: object, **options: object) -> None:
        self.stdout.write("Hub worker started")
        last_poll = 0.0
        last_maintenance = 0.0
        last_call_sweep = 0.0
        while True:
            try:
                event = claim_next_outbox_event()
            except Exception:  # pragma: no cover
                # Отравленное событие не должно ронять процесс: иначе воркер
                # уходит в краш-петлю и вместе с outbox встают поллинг
                # мессенджеров и таймауты звонков.
                logger.exception("Outbox claim cycle failed")
                time.sleep(1)
                continue
            if event is not None:
                try:
                    logger.info("Processing outbox event %s", event.id)
                    dispatch(event)
                    event.status = OutboxStatus.PROCESSED
                    event.processed_at = timezone.now()
                    event.save(
                        using="platform",
                        update_fields=["status", "processed_at"],
                    )
                except Exception as exc:  # pragma: no cover
                    logger.exception("Outbox event failed: %s", event.id)
                    mark_retry(event, str(exc))

            # Дальше идут периодические работы. Раньше обработка события
            # обрывала цикл на `continue`, и при непрерывном потоке событий —
            # а породить его может кто угодно через публичный виджет —
            # переставали забираться входящие сообщения и истекать приглашения
            # на звонки. Проверки дешёвые: почти всегда это сравнение времени.
            now = time.monotonic()
            if now - last_poll >= MESSENGER_POLL_INTERVAL:
                last_poll = now
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            poll_all_messengers(context)
                except Exception:  # pragma: no cover
                    logger.exception("Messenger polling cycle failed")
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            poll_notifier_bots(context)
                except Exception:  # pragma: no cover
                    logger.exception("Notifier polling cycle failed")
            if now - last_call_sweep >= CALL_SWEEP_INTERVAL:
                last_call_sweep = now
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            expire_stale_calls(context)
                except Exception:  # pragma: no cover
                    logger.exception("Call sweep cycle failed")
            if now - last_maintenance >= MAINTENANCE_INTERVAL:
                last_maintenance = now
                # Канал релизов спрашивается не чаще раза в несколько часов:
                # интервал держит сама проверка по времени последнего ответа.
                try:
                    check_for_updates()
                except Exception:  # pragma: no cover
                    logger.exception("Update check cycle failed")
                try:
                    for context in self._tenant_contexts():
                        with tenant_atomic(context):
                            close_stale_conversations(context)
                except Exception:  # pragma: no cover
                    logger.exception("Maintenance cycle failed")
                try:
                    # Просроченные сессии Django сам не удаляет, а их накопление
                    # утяжеляет карточку сотрудника: владельца сессии видно
                    # только внутри её содержимого (chatballs.identity.sessions).
                    call_command("clearsessions")
                except Exception:  # pragma: no cover
                    logger.exception("Session cleanup failed")
            # Спим только когда работы нет: иначе очередь событий разбиралась бы
            # по одному событию в секунду.
            if event is None:
                time.sleep(1)
