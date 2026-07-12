import { CallView, type CallViewMode, type CallViewStatus, useCallRtcSession, useLoopingAudio } from "@edevs/ui";
import { Modal } from "antd";
import { useEffect, useMemo, useState } from "react";

import { channelMeta } from "./data";
import type { ApiCall, CallAccess } from "./model";
import type { ConversationListItem } from "./types";
import "./call.css";

const TERMINAL: Record<string, { icon: CallViewStatus["icon"]; title: string; caption: (name: string) => string; tone: "neutral" | "error" | "warn"; retry?: string }> = {
  DECLINED: { icon: "declined", title: "Звонок отклонён", caption: (name) => `${name} отклонил(а) вызов.`, tone: "neutral", retry: "Позвонить снова" },
  MISSED: { icon: "missed", title: "Пропущенный звонок", caption: (name) => `${name} не ответил(а) на вызов.`, tone: "warn", retry: "Перезвонить" },
  EXPIRED: { icon: "clock", title: "Время ожидания истекло", caption: () => "Никто не ответил вовремя. Попробуйте позвонить снова.", tone: "warn", retry: "Позвонить снова" },
  CANCELLED: { icon: "declined", title: "Звонок отменён", caption: () => "Приглашение отменено.", tone: "neutral" },
  FAILED: { icon: "alert", title: "Не удалось соединиться", caption: () => "Проверьте интернет-соединение и попробуйте снова.", tone: "error", retry: "Повторить" },
  ENDED: { icon: "declined", title: "Звонок завершён", caption: () => "Разговор завершён.", tone: "neutral" },
};

type Props = {
  open: boolean;
  dialog: ConversationListItem | null;
  call: ApiCall | null;
  access: CallAccess | null;
  errorText: string;
  onCallChange: (call: ApiCall) => void;
  onCancel: () => void;
  onRetry: () => void;
  onClose: () => void;
};

export function CallOverlay(props: Props) {
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
  useLoopingAudio("/audio/ringtone.mp3", props.open && mode === "ringing", 0.5);
  const status = useMemo(
    () => buildStatus(props, rtc.connectionPhase, rtc.mediaIssue, rtc.restart, rtc.prepare, rtc.start),
    [props, rtc.connectionPhase, rtc.mediaIssue, rtc.restart, rtc.prepare, rtc.start],
  );

  if (!props.dialog) return null;
  const channel = channelMeta[props.dialog.channel];
  const subtitle = subtitleFor(mode, call, status);
  const mediaCaption = rtc.mediaIssue === "devices" ? "Нет доступа к камере и микрофону" : rtc.mediaIssue === "video" ? "Камера недоступна" : "Камера выключена";
  const endAndClose = () => {
    if (mode === "active" || mode === "reconnecting" || mode === "connecting") rtc.end();
    props.onClose();
  };

  return (
    <Modal open={props.open} onCancel={endAndClose} footer={null} closable={false} width={428} className="call-modal" destroyOnHidden>
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
        onJoin={rtc.start}
        onCancel={mode === "ringing" ? props.onCancel : endAndClose}
        onEnd={rtc.end}
        onClose={endAndClose}
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
  if (props.errorText) return { icon: "alert", tone: "error", title: "Не удалось запросить звонок", caption: props.errorText };
  if (mediaIssue === "unsupported") return { icon: "unsupported", tone: "error", title: "Видеозвонки не поддерживаются", caption: "Обновите браузер или откройте ссылку в Chrome, Safari или Edge." };
  if (mediaIssue === "devices") return {
    icon: "alert",
    tone: "error",
    title: "Нет доступа к камере и микрофону",
    caption: "Разрешите доступ к устройствам в настройках браузера и повторите.",
    actions: [
      { label: "Повторить проверку", kind: "primary", onClick: onPrepare },
      { label: "Без видео", kind: "secondary", onClick: onJoin },
    ],
  };
  if (connection === "failed") return {
    icon: "alert",
    tone: "error",
    title: "Не удалось соединиться",
    caption: "Проверьте интернет-соединение и попробуйте снова.",
    actions: [{ label: "Повторить", kind: "primary", onClick: onReconnect }],
  };
  if (!props.call) return undefined;
  if (props.call.status === "ACCEPTED" || props.call.status === "CONNECTING") return { icon: "spinner", tone: "neutral", title: "Соединяем звонок", caption: "Устанавливаем защищённое соединение…" };
  const terminal = TERMINAL[props.call.status];
  if (!terminal) return undefined;
  const duration = props.call.status === "ENDED" && props.call.durationSeconds != null ? `Длительность ${formatDuration(props.call.durationSeconds)}. ` : "";
  return {
    icon: terminal.icon,
    tone: terminal.tone,
    title: terminal.title,
    caption: `${duration}${terminal.caption(props.dialog?.name ?? "Клиент")}`,
    actions: [
      ...(terminal.retry ? [{ label: terminal.retry, kind: "primary" as const, onClick: props.onRetry }] : []),
      { label: "Закрыть", kind: "secondary" as const, onClick: props.onClose },
    ],
  };
}

function subtitleFor(mode: CallViewMode, call: ApiCall | null, status?: CallViewStatus) {
  if (mode === "ringing") return call?.status === "REQUESTED" ? "Отправляем приглашение" : "Ожидание ответа";
  if (mode === "precall") return "Проверьте камеру и микрофон";
  if (mode === "active") return "Активный звонок";
  if (mode === "reconnecting") return "Переподключение";
  return status?.title ?? "Соединение";
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
