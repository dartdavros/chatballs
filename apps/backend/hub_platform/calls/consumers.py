"""WebSocket signaling звонков (SPEC-HUB-0013 §9).

Правила:
- аутентификация первым сообщением {"type": "auth", "token": <call access token>}
  — token не попадает в URL, логи и историю прокси;
- в комнате только два разрешённых участника конкретной CallSession;
- SDP и ICE не сохраняются и не логируются (payload событий не пишется в логи);
- поздние события завершённого звонка игнорируются;
- reconnect WebSocket не создаёт новую CallSession — только presence-статусы.
"""

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from hub_platform.calls import signaling
from hub_platform.calls.errors import CallTokenError
from hub_platform.calls.models import TERMINAL_CALL_STATUSES
from hub_platform.calls.services import authorize_call_access_token

logger = logging.getLogger(__name__)

AUTH_TIMEOUT_CLOSE = 4401
# События, которые сервер только ретранслирует второму участнику.
RELAY_TYPES = {"webrtc.offer", "webrtc.answer", "webrtc.ice_candidate", "participant.media_state"}
SEEN_COMMANDS_LIMIT = 512


class CallSignalingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.call_id = None
        self.side = None
        self.group = None
        self._seen_commands: set[str] = set()
        await self.accept()

    async def receive_json(self, content: dict, **kwargs) -> None:
        msg_type = content.get("type")
        if self.call_id is None:
            await self._authenticate(msg_type, content)
            return

        # Идемпотентность command-событий: повтор с тем же id игнорируется.
        command_id = content.get("id")
        if isinstance(command_id, str) and command_id:
            if command_id in self._seen_commands:
                return
            if len(self._seen_commands) >= SEEN_COMMANDS_LIMIT:
                self._seen_commands.clear()
            self._seen_commands.add(command_id)

        if msg_type in RELAY_TYPES:
            await self._relay(msg_type, content)
        elif msg_type == "participant.connection_state":
            await self._connection_state(content)
        elif msg_type == "call.ended":
            payload = await database_sync_to_async(signaling.end_from_signaling)(self.call_id, self.side)
            await self._broadcast({"type": "call.state", "call": payload}, include_self=True)
        # незнакомые типы игнорируются без разрыва соединения

    async def disconnect(self, code: int) -> None:
        if self.group is None:
            return
        await self.channel_layer.group_discard(self.group, self.channel_name)
        payload = await database_sync_to_async(signaling.signaling_leave)(self.call_id, self.side)
        if payload is not None:
            await self._broadcast(
                {"type": "participant.connection_state", "side": self.side, "state": "DISCONNECTED"},
            )

    # --- шаги протокола ---

    async def _authenticate(self, msg_type, content: dict) -> None:
        if msg_type != "auth":
            await self.close(code=AUTH_TIMEOUT_CLOSE)
            return
        token = str(content.get("token", ""))
        try:
            claims, call = await database_sync_to_async(
                lambda: authorize_call_access_token(token=token)
            )()
        except CallTokenError:
            await self.send_json({"type": "error", "code": "AUTH_FAILED"})
            await self.close(code=AUTH_TIMEOUT_CLOSE)
            return
        self.call_id = call.id
        self.side = claims.side
        self.group = f"call.{call.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        payload = await database_sync_to_async(signaling.signaling_join)(self.call_id, self.side)
        await self.send_json({"type": "call.state", "call": payload})
        await self._broadcast({"type": "peer.joined", "side": self.side})
        logger.info("call signaling joined: call=%s side=%s", self.call_id, self.side)

    async def _relay(self, msg_type: str, content: dict) -> None:
        # Сервер валидирует состояние CallSession перед передачей (SPEC §9);
        # payload не логируется — там SDP/ICE.
        status = await database_sync_to_async(signaling.call_status)(self.call_id)
        if status in TERMINAL_CALL_STATUSES:
            return
        if msg_type == "webrtc.offer":
            changed = await database_sync_to_async(signaling.start_negotiation)(self.call_id)
            if changed is not None:
                await self._broadcast({"type": "call.state", "call": changed}, include_self=True)
        await self._broadcast({**content, "side": self.side})

    async def _connection_state(self, content: dict) -> None:
        connected = content.get("state") == "CONNECTED"
        payload, became_active = await database_sync_to_async(signaling.report_connection)(
            self.call_id, self.side, connected
        )
        await self._broadcast(
            {"type": "participant.connection_state", "side": self.side, "state": str(content.get("state", ""))[:16]},
        )
        if became_active and payload is not None:
            await self._broadcast({"type": "call.state", "call": payload}, include_self=True)

    # --- fan-out ---

    async def _broadcast(self, payload: dict, *, include_self: bool = False) -> None:
        await self.channel_layer.group_send(
            self.group,
            {"type": "call.message", "payload": payload, "sender": self.channel_name, "include_self": include_self},
        )

    async def call_message(self, event: dict) -> None:
        if not event.get("include_self") and event.get("sender") == self.channel_name:
            return
        await self.send_json(event["payload"])
