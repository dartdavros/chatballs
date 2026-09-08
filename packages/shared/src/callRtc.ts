/**
 * Клиент P2P-звонка: собственный WebSocket signaling Hub + RTCPeerConnection
 * (SPEC-CHATBALLS-0013 §9–10). Общий для internal-ui (оператор) и web-chat (клиент).
 *
 * Роли детерминированы: offer всегда создаёт STAFF (инициатор), CUSTOMER
 * только отвечает — glare исключён. Mute/выключение камеры — track.enabled,
 * без пересоздания звонка. Access token уходит только первым сообщением
 * auth (не в URL). SDP/ICE нигде не сохраняются.
 */

export type CallSide = "STAFF" | "CUSTOMER";

export type PublicCallState = {
  callId: string;
  status: string;
  staffName?: string;
  endedBy?: string | null;
  durationSeconds?: number | null;
};

export type RtcConnectionPhase = "connecting" | "connected" | "reconnecting" | "failed";

export type CallRtcHandlers = {
  onCallState?: (call: PublicCallState) => void;
  onRemoteStream?: (stream: MediaStream) => void;
  onRemoteMedia?: (state: { mic: boolean; cam: boolean }) => void;
  onConnection?: (phase: RtcConnectionPhase) => void;
  onClosed?: () => void;
};

const WS_RETRY_LIMIT = 5;

function commandId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}

export class CallRtcClient {
  private ws: WebSocket | null = null;
  private pc: RTCPeerConnection | null = null;
  private disposed = false;
  private authed = false;
  private wsRetries = 0;
  private negotiating = false;
  private endRequested = false;
  private pendingCandidates: RTCIceCandidateInit[] = [];

  constructor(
    private readonly options: {
      accessToken: string;
      side: CallSide;
      iceServers: RTCIceServer[];
      localStream: MediaStream | null;
      handlers: CallRtcHandlers;
    },
  ) {}

  start(): void {
    this.openSocket();
  }

  /** Завершить звонок со своей стороны (идемпотентно на сервере). */
  end(): void {
    this.endRequested = true;
    if (this.authed) this.sendCommand({ type: "call.ended" });
  }

  /** Тихо закрыть соединения (уход со страницы, терминальное состояние). */
  dispose(): void {
    this.disposed = true;
    this.pc?.close();
    this.pc = null;
    this.ws?.close();
    this.ws = null;
  }

  /** Состояние устройств: track.enabled + уведомление собеседника. */
  setMediaState(mic: boolean, cam: boolean): void {
    this.options.localStream?.getAudioTracks().forEach((track) => {
      track.enabled = mic;
    });
    this.options.localStream?.getVideoTracks().forEach((track) => {
      track.enabled = cam;
    });
    this.sendCommand({ type: "participant.media_state", mic, cam });
  }

  // --- WebSocket signaling ---

  private openSocket(): void {
    if (this.disposed) return;
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${scheme}://${location.host}/ws/calls/`);
    this.ws = ws;
    this.authed = false;
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "auth", token: this.options.accessToken }));
    };
    ws.onmessage = (event) => {
      let message: Record<string, unknown>;
      try {
        message = JSON.parse(String(event.data));
      } catch {
        return;
      }
      void this.route(message);
    };
    ws.onclose = () => {
      if (this.disposed) return;
      // Reconnect signaling не создаёт новую CallSession (SPEC §9).
      if (this.wsRetries >= WS_RETRY_LIMIT) {
        this.options.handlers.onConnection?.("failed");
        return;
      }
      this.wsRetries += 1;
      setTimeout(() => this.openSocket(), Math.min(500 * 2 ** this.wsRetries, 5000));
    };
  }

  private sendCommand(payload: Record<string, unknown>): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ id: commandId(), ...payload }));
  }

  private async route(message: Record<string, unknown>): Promise<void> {
    switch (message.type) {
      case "error":
        this.options.handlers.onConnection?.("failed");
        this.dispose();
        this.options.handlers.onClosed?.();
        return;
      case "call.state": {
        if (!this.authed) {
          this.authed = true;
          this.wsRetries = 0;
          if (this.endRequested) {
            this.sendCommand({ type: "call.ended" });
            return;
          }
          this.publishMediaState();
          // STAFF мог подключиться позже клиента: peer.joined уже прошёл.
          if (this.options.side === "STAFF") void this.sendOffer(false);
        }
        this.options.handlers.onCallState?.(message.call as PublicCallState);
        return;
      }
      case "peer.joined":
        if (this.options.side === "STAFF") void this.sendOffer(this.pc != null);
        return;
      case "webrtc.offer":
        await this.acceptOffer(String(message.sdp ?? ""));
        return;
      case "webrtc.answer":
        if (this.pc && this.pc.signalingState === "have-local-offer") {
          await this.pc.setRemoteDescription({ type: "answer", sdp: String(message.sdp ?? "") });
          await this.flushCandidates();
        }
        return;
      case "webrtc.ice_candidate":
        if (message.candidate) await this.addCandidate(message.candidate as RTCIceCandidateInit);
        return;
      case "participant.media_state":
        this.options.handlers.onRemoteMedia?.({ mic: message.mic !== false, cam: message.cam !== false });
        return;
      case "participant.connection_state":
        if (message.state === "DISCONNECTED" || message.state === "RECONNECTING") {
          this.options.handlers.onConnection?.("reconnecting");
        }
        return;
      default:
        return;
    }
  }

  // --- RTCPeerConnection ---

  private ensurePeer(): RTCPeerConnection {
    if (this.pc) return this.pc;
    const pc = new RTCPeerConnection({ iceServers: this.options.iceServers });
    this.pc = pc;
    this.options.localStream?.getTracks().forEach((track) => {
      pc.addTrack(track, this.options.localStream as MediaStream);
    });
    pc.ontrack = (event) => {
      const stream = event.streams[0] ?? new MediaStream([event.track]);
      this.options.handlers.onRemoteStream?.(stream);
    };
    pc.onicecandidate = (event) => {
      if (event.candidate) this.sendCommand({ type: "webrtc.ice_candidate", candidate: event.candidate.toJSON() });
    };
    pc.onconnectionstatechange = () => {
      switch (pc.connectionState) {
        case "connected":
          this.sendCommand({ type: "participant.connection_state", state: "CONNECTED" });
          this.options.handlers.onConnection?.("connected");
          void this.reportMetrics();
          break;
        case "disconnected":
          this.sendCommand({ type: "participant.connection_state", state: "RECONNECTING" });
          this.options.handlers.onConnection?.("reconnecting");
          if (this.options.side === "STAFF") void this.sendOffer(true);
          break;
        case "failed":
          this.sendCommand({ type: "participant.connection_state", state: "RECONNECTING" });
          this.options.handlers.onConnection?.("reconnecting");
          if (this.options.side === "STAFF") void this.sendOffer(true);
          else this.options.handlers.onConnection?.("failed");
          break;
        default:
          break;
      }
    };
    return pc;
  }

  /**
   * Технические метрики соединения (SPEC §13): только КАТЕГОРИЯ выбранного
   * ICE-кандидата (host/srflx/relay) и RTT — чтобы отличить direct от TURN relay.
   * Ни SDP, ни адреса кандидатов, ни медиаданные не отправляются.
   */
  private async reportMetrics(): Promise<void> {
    const pc = this.pc;
    if (!pc) return;
    try {
      const stats = await pc.getStats();
      const get = (id: unknown): Record<string, unknown> | undefined =>
        typeof id === "string" ? (stats.get(id) as Record<string, unknown> | undefined) : undefined;
      let selectedId = "";
      let pair: Record<string, unknown> | null = null;
      stats.forEach((report) => {
        const entry = report as Record<string, unknown>;
        if (entry.type === "transport" && typeof entry.selectedCandidatePairId === "string") {
          selectedId = entry.selectedCandidatePairId;
        }
      });
      stats.forEach((report) => {
        const entry = report as Record<string, unknown>;
        if (entry.type !== "candidate-pair") return;
        if (entry.id === selectedId || (!pair && entry.nominated === true && entry.state === "succeeded")) {
          pair = entry;
        }
      });
      const selected = pair as Record<string, unknown> | null;
      if (!selected) return;
      const candidateType = (id: unknown): string => {
        const type = get(id)?.candidateType;
        return typeof type === "string" ? type : "";
      };
      const rtt = selected.currentRoundTripTime;
      this.sendCommand({
        type: "participant.metrics",
        localCandidateType: candidateType(selected.localCandidateId),
        remoteCandidateType: candidateType(selected.remoteCandidateId),
        roundTripMs: typeof rtt === "number" ? Math.round(rtt * 1000) : null,
      });
    } catch {
      /* getStats недоступен/прерван — метрики необязательны */
    }
  }

  private publishMediaState(): void {
    const audio = this.options.localStream?.getAudioTracks()[0];
    const video = this.options.localStream?.getVideoTracks()[0];
    this.sendCommand({
      type: "participant.media_state",
      mic: audio?.enabled ?? false,
      cam: video?.enabled ?? false,
    });
  }

  private async sendOffer(iceRestart: boolean): Promise<void> {
    if (this.disposed || this.negotiating) return;
    this.negotiating = true;
    try {
      const pc = this.ensurePeer();
      const offer = await pc.createOffer(iceRestart ? { iceRestart: true } : undefined);
      await pc.setLocalDescription(offer);
      this.sendCommand({ type: "webrtc.offer", sdp: offer.sdp });
    } catch {
      this.options.handlers.onConnection?.("failed");
    } finally {
      this.negotiating = false;
    }
  }

  private async acceptOffer(sdp: string): Promise<void> {
    if (this.disposed || this.options.side !== "CUSTOMER") return;
    try {
      const pc = this.ensurePeer();
      await pc.setRemoteDescription({ type: "offer", sdp });
      await this.flushCandidates();
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      this.sendCommand({ type: "webrtc.answer", sdp: answer.sdp });
    } catch {
      this.options.handlers.onConnection?.("failed");
    }
  }

  private async addCandidate(candidate: RTCIceCandidateInit): Promise<void> {
    if (!this.pc?.remoteDescription) {
      this.pendingCandidates.push(candidate);
      return;
    }
    try {
      await this.pc.addIceCandidate(candidate);
    } catch {
      /* кандидат от устаревшей negotiation — игнорируем */
    }
  }

  private async flushCandidates(): Promise<void> {
    if (!this.pc?.remoteDescription) return;
    const candidates = this.pendingCandidates.splice(0);
    for (const candidate of candidates) await this.addCandidate(candidate);
  }
}
