// Видеозвонок (оператор): antd Modal + CallView. Путь видео не меняется — вынесен
// из CallOverlay при добавлении аудиозвонка, чтобы CallOverlay остался тонким
// диспетчером по call.kind (NO GOD / separation of concerns).

import { CallView, type CallViewMode, type CallViewStatus, isTerminalCallStatus, useCallRtcSession, useLoopingAudio } from "@chatballs/ui";
import { Modal } from "antd";
import { useEffect, useState } from "react";

import { providerMeta } from "../../shared/providers";
import { endCallByAccess, type ApiCall, type CallAccess } from "./model";
import type { ConversationListItem } from "./types";
import "./call.css";
import { t } from "../../i18n";

const TERMINAL: Record<string, { icon: CallViewStatus["icon"]; title: string; caption: (name: string) => string; tone: "neutral" | "error" | "warn"; retry?: string }> = {
  DECLINED: { icon: "declined", title: t("conversations.call_declined"), caption: (name) => t("conversations.call_declined_by", { name }), tone: "neutral", retry: t("conversations.call_again") },
  MISSED: { icon: "missed", title: t("conversations.missed_call"), caption: (name) => t("conversations.call_unanswered_by", { name }), tone: "warn", retry: t("conversations.call_back") },
  EXPIRED: { icon: "clock", title: t("conversations.wait_timed_out"), caption: () => t("conversations.nobody_answered_time_try_calling"), tone: "warn", retry: t("conversations.call_again") },
  CANCELLED: { icon: "declined", title: t("conversations.call_cancelled"), caption: () => t("conversations.invitation_was_cancelled"), tone: "neutral" },
  FAILED: { icon: "alert", title: t("conversations.could_not_connect"), caption: () => t("conversations.check_internet_connection_try_again"), tone: "error", retry: t("common.try_again") },
  ENDED: { icon: "declined", title: t("conversations.call_ended"), caption: () => t("conversations.conversation_has_ended"), tone: "neutral" },
};

type Props = {
  open: boolean;
  dialog: ConversationListItem | null;
  call: ApiCall | null;
  requestedKind?: ApiCall["kind"] | null;
  access: CallAccess | null;
  errorText: string;
  onCallChange: (call: ApiCall) => void;
  onCancel: () => void;
  onRetry: () => void;
  onClose: () => void;
};

export function VideoCallOverlay(props: Props) {
  const call = props.call;
  const rtc = useCallRtcSession({
    resetKey: call?.id ?? "",
    previewEnabled: props.open && call?.status === "ACCEPTED",
    accessToken: props.access?.accessToken ?? "",
    side: "STAFF",
    iceServers: props.access?.iceServers ?? [],
    onCallState: (state) => {
      if (call) props.onCallChange({ ...call, status: state.status as ApiCall["status"], endedBy: state.endedBy ?? null, durationSeconds: state.durationSeconds ?? null });
    },
  });
  const elapsed = useElapsed(call?.connectedAt ?? null, call?.status === "ACTIVE");
  const mode = resolveMode(call, props.errorText, rtc.connectionPhase, rtc.mediaIssue);

  // Камеру и микрофон держим только пока оверлей открыт и звонок не завершён.
  // Терминал приходит и поллингом состояния, а не только по RTC-сокету: до
  // «Присоединиться» сокета ещё нет, и без явной остановки камера оператора
  // продолжала гореть после отбоя клиента.
  useEffect(() => {
    if (!props.open || isTerminalCallStatus(call?.status)) rtc.stop();
  }, [props.open, call?.status, rtc.stop]);
  useLoopingAudio("/audio/ringtone.mp3", props.open && mode === "ringing", 0.5);
  // Без useMemo: `props` — новый объект на каждом рендере, поэтому обёртка всё
  // равно пересчитывалась каждый раз, а идентичность результата никому не нужна
  // (CallView не мемоизирован). Как в AudioCallOverlay — считаем на месте.
  const status = buildStatus(props, rtc.connectionPhase, rtc.mediaIssue, rtc.restart, rtc.prepare, rtc.start);

  if (!props.dialog) return null;
  const channel = providerMeta[props.dialog.channel];
  const subtitle = subtitleFor(mode, call, status);
  const mediaCaption = rtc.mediaIssue === "devices" ? t("conversations.no_access_camera_microphone") : rtc.mediaIssue === "video" ? t("conversations.camera_unavailable") : t("conversations.camera_off");
  const finish = async () => {
    const token = props.access?.accessToken;
    if (!token || !call || TERMINAL[call.status]) return;
    try { props.onCallChange(await endCallByAccess(token)); }
    finally { rtc.stop(); }
  };
  const endAndClose = async () => {
    if (mode === "active" || mode === "reconnecting" || mode === "connecting" || mode === "precall") await finish();
    props.onClose();
  };

  return (
    <Modal open={props.open} onCancel={() => void endAndClose()} footer={null} closable={false} width={428} className="call-modal" destroyOnHidden>
      <CallView
        mode={mode}
        peerName={props.dialog.name}
        peerInitials={props.dialog.initials}
        peerAvatarColor={props.dialog.avatarBg}
        subtitle={subtitle}
        channelBadge={<em className="call-channel" style={{ background: channel.bg, color: channel.color }}>{channel.label}</em>}
        localStream={rtc.localStream}
        remoteStream={rtc.remoteStream}
        micOn={rtc.micOn}
        camOn={rtc.camOn}
        remoteMicOn={rtc.remoteMicOn}
        remoteCamOn={rtc.remoteCamOn}
        mediaCaption={mediaCaption}
        elapsedSeconds={elapsed}
        status={status}
        joining={rtc.preparing || rtc.connectionPhase === "connecting"}
        onToggleMic={rtc.toggleMic}
        onToggleCam={rtc.toggleCam}
        onJoin={() => void rtc.start()}
        onCancel={mode === "ringing" ? props.onCancel : () => void endAndClose()}
        onEnd={() => void finish()}
        onClose={() => void endAndClose()}
      />
    </Modal>
  );
}

function resolveMode(call: ApiCall | null, errorText: string, connection: string, mediaIssue: string): CallViewMode {
  if (errorText || !call || TERMINAL[call.status] || connection === "failed" || mediaIssue === "devices" || mediaIssue === "unsupported") return "status";
  if (call.status === "REQUESTED" || call.status === "RINGING") return "ringing";
  if (call.status === "ACCEPTED" && connection === "idle") return "precall";
  if (connection === "reconnecting") return "reconnecting";
  if (call.status === "ACTIVE" || connection === "connected") return "active";
  return "connecting";
}

function buildStatus(props: Props, connection: string, mediaIssue: string, onReconnect: () => void, onPrepare: () => void, onJoin: () => void): CallViewStatus | undefined {
  if (props.errorText) return { icon: "alert", tone: "error", title: t("conversations.could_not_request_call"), caption: props.errorText };
  if (mediaIssue === "unsupported") return { icon: "unsupported", tone: "error", title: t("conversations.video_calls_not_supported"), caption: t("conversations.update_browser_or_open_link") };
  if (mediaIssue === "devices") return {
    icon: "alert",
    tone: "error",
    title: t("conversations.no_access_camera_microphone"),
    caption: t("conversations.allow_device_access_browser_settings"),
    actions: [
      { label: t("conversations.check_again"), kind: "primary", onClick: onPrepare },
      { label: t("conversations.without_video"), kind: "secondary", onClick: onJoin },
    ],
  };
  if (connection === "failed") return {
    icon: "alert",
    tone: "error",
    title: t("conversations.could_not_connect"),
    caption: t("conversations.check_internet_connection_try_again"),
    actions: [{ label: t("common.try_again"), kind: "primary", onClick: onReconnect }],
  };
  if (!props.call) return undefined;
  if (props.call.status === "ACCEPTED" || props.call.status === "CONNECTING") return { icon: "spinner", tone: "neutral", title: t("conversations.connecting_call"), caption: t("conversations.establishing_secure_connection") };
  const terminal = TERMINAL[props.call.status];
  if (!terminal) return undefined;
  const duration = props.call.status === "ENDED" && props.call.durationSeconds != null ? `${t("time.duration_is", { duration: formatDuration(props.call.durationSeconds) })} ` : "";
  return {
    icon: terminal.icon,
    tone: terminal.tone,
    title: terminal.title,
    caption: `${duration}${terminal.caption(props.dialog?.name ?? t("conversations.customer"))}`,
    actions: [
      ...(terminal.retry ? [{ label: terminal.retry, kind: "primary" as const, onClick: props.onRetry }] : []),
      { label: t("common.close"), kind: "secondary" as const, onClick: props.onClose },
    ],
  };
}

function subtitleFor(mode: CallViewMode, call: ApiCall | null, status?: CallViewStatus) {
  if (mode === "ringing") return call?.status === "REQUESTED" ? t("conversations.sending_invitation") : t("conversations.waiting_answer");
  if (mode === "precall") return t("conversations.check_camera_microphone");
  if (mode === "active") return t("conversations.active_call");
  if (mode === "reconnecting") return t("conversations.reconnecting");
  return status?.title ?? t("conversations.connecting");
}

function useElapsed(connectedAt: string | null, active: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!connectedAt || !active) return;
    const update = () => setSeconds(Math.max(0, Math.floor((Date.now() - new Date(connectedAt).getTime()) / 1000)));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [active, connectedAt]);
  return seconds;
}

function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
