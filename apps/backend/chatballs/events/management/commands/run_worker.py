import logging
import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from chatballs.calls.maintenance import expire_stale_calls
from chatballs.conversations.escalation import sweep_waiting_conversations
from chatballs.conversations.maintenance import close_stale_conversations
from chatballs.conversations.poller import poll_all_messengers
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxStatus
from chatballs.events.services import (
    OUTBOX_DB,
    claim_next_outbox_event,
    mark_retry,
    release_stale_processing,
)
from chatballs.notifications.binding import poll_notifier_bots
from chatballs.ratings.web_delivery import deliver_due_requests
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import iter_organizations
from chatballs.updates.services import check_for_updates
from chatballs.integrations.execution.retention import cleanup as cleanup_scenario_data

logger = logging.getLogger(__name__)

# Роли воркера. Разделены потому, что работы у них разного веса: опрос
# подключений — это короткие запросы и записи в базу, а обработка событий может
# ждать модель десятки секунд. В одном процессе второе перекрывало первое, и
# входящие переставали забираться на всё время ответа AI.
ROLE_ALL = "all"
ROLE_POLLER = "poller"
ROLE_EVENTS = "events"

MESSENGER_POLL_INTERVAL = 3.0  # seconds between messenger long-poll cycles
MAINTENANCE_INTERVAL = 3600.0  # seconds between maintenance cycles (auto-close stale dialogs)
CALL_SWEEP_INTERVAL = 10.0  # seconds between call timeout sweeps (invite expiry, stuck connect)
# Пороги очереди задаются в минутах, поэтому раз в полминуты — с запасом:
# проверка дешёвая, а повтор гасится dedup-ключом уровня.
QUEUE_SWEEP_INTERVAL = 30.0  # seconds between waiting-queue escalation sweeps
# Возврат событий, взятых в работу упавшим процессом.
STALE_SWEEP_INTERVAL = 60.0


class Command(BaseCommand):
    help = (
        "Runs the local domain event worker. Roles: 'poller' polls messenger "
        "connections and runs sweeps, 'events' dispatches the outbox (AI turns), "
        "'all' does both in one process (development default)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--role",
            choices=[ROLE_ALL, ROLE_POLLER, ROLE_EVENTS],
            default=os.environ.get("CHATBALLS_WORKER_ROLE", ROLE_ALL),
            help=(
                "Что делает этот процесс. Опрос держат в одном экземпляре "
                "(курсоры подключений и паузы после сбоя живут в его памяти), "
                "роль событий масштабируется репликами."
            ),
        )

    @staticmethod
    def _tenant_contexts():
        for organization in iter_organizations():
            yield TenantContext.for_resource(
                organization, actor_kind=TenantActorKind.SYSTEM
            )

    def _for_each_tenant(self, operation, failure: str) -> None:
        try:
            for context in self._tenant_contexts():
                with tenant_atomic(context):
                    operation(context)
        except Exception:  # pragma: no cover
            logger.exception(failure)

    def _dispatch_one(self) -> bool:
        """Взять и обработать одно событие. False — событий нет."""

        try:
            event = claim_next_outbox_event()
        except Exception:  # pragma: no cover
            # Отравленное событие не должно ронять процесс: иначе воркер
            # уходит в краш-петлю и вместе с outbox встают поллинг
            # мессенджеров и таймауты звонков.
            logger.exception("Outbox claim cycle failed")
            time.sleep(1)
            return False
        if event is None:
            return False
        try:
            logger.info("Processing outbox event %s", event.id)
            dispatch(event)
            event.status = OutboxStatus.PROCESSED
            event.processed_at = timezone.now()
            event.save(
                using=OUTBOX_DB,
                update_fields=["status", "processed_at"],
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Outbox event failed: %s", event.id)
            mark_retry(event, str(exc))
        return True

    def handle(self, *args: object, **options: object) -> None:
        role = str(options["role"])
        does_events = role in (ROLE_ALL, ROLE_EVENTS)
        does_polling = role in (ROLE_ALL, ROLE_POLLER)
        self.stdout.write(f"Chatballs worker started (role={role})")
        last_poll = 0.0
        last_maintenance = 0.0
        last_call_sweep = 0.0
        last_queue_sweep = 0.0
        last_stale_sweep = 0.0
        while True:
            worked = self._dispatch_one() if does_events else False

            # Дальше идут периодические работы. Раньше обработка события
            # обрывала цикл на `continue`, и при непрерывном потоке событий —
            # а породить его может кто угодно через публичный виджет —
            # переставали забираться входящие сообщения и истекать приглашения
            # на звонки. Проверки дешёвые: почти всегда это сравнение времени.
            now = time.monotonic()
            if does_events and now - last_stale_sweep >= STALE_SWEEP_INTERVAL:
                last_stale_sweep = now
                try:
                    released = release_stale_processing()
                    if released:
                        logger.warning("Released %s stale outbox event(s)", released)
                except Exception:  # pragma: no cover
                    logger.exception("Stale outbox sweep failed")
            if does_polling and now - last_poll >= MESSENGER_POLL_INTERVAL:
                last_poll = now
                self._for_each_tenant(poll_all_messengers, "Messenger polling cycle failed")
                self._for_each_tenant(poll_notifier_bots, "Notifier polling cycle failed")
                self._for_each_tenant(deliver_due_requests, "Rating delivery cycle failed")
            if does_polling and now - last_call_sweep >= CALL_SWEEP_INTERVAL:
                last_call_sweep = now
                self._for_each_tenant(expire_stale_calls, "Call sweep cycle failed")
            if does_polling and now - last_queue_sweep >= QUEUE_SWEEP_INTERVAL:
                last_queue_sweep = now
                self._for_each_tenant(
                    sweep_waiting_conversations, "Waiting queue sweep cycle failed"
                )
            if does_polling and now - last_maintenance >= MAINTENANCE_INTERVAL:
                last_maintenance = now
                # Канал релизов спрашивается не чаще раза в несколько часов:
                # интервал держит сама проверка по времени последнего ответа.
                try:
                    check_for_updates()
                except Exception:  # pragma: no cover
                    logger.exception("Update check cycle failed")
                self._for_each_tenant(close_stale_conversations, "Maintenance cycle failed")
                self._for_each_tenant(cleanup_scenario_data, "Scenario retention cycle failed")
                try:
                    # Просроченные сессии Django сам не удаляет, а их накопление
                    # утяжеляет карточку сотрудника: владельца сессии видно
                    # только внутри её содержимого (chatballs.identity.sessions).
                    call_command("clearsessions")
                except Exception:  # pragma: no cover
                    logger.exception("Session cleanup failed")
            # Спим только когда работы нет: иначе очередь событий разбиралась бы
            # по одному событию в секунду.
            if not worked:
                time.sleep(1)
