// Аудиозвонок (оператор): antd Modal + AudioCallView (baseline «Аудиозвонок.dc.html»).
// Видео не запрашивается. Флоу: incoming/ringing → connecting → active → терминал,
// без pre-call (нет этапа проверки камеры). Параллель VideoCallOverlay, но под аудио.

import { AudioCallView, type AudioCallMode, buildAudioStatus, isTerminalCallStatus, useCallRtcSession, useLoopingAudio } from "@chatballs/ui";
import { Modal } from "antd";
import { useEffect, useState } from "react";

import { providerMeta } from "../../shared/providers";
import { endCallByAccess, type ApiCall, type CallAccess } from "./model";
import type { ConversationListItem } from "./types";
import "./call.css";

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

export function AudioCallOverlay(props: Props) {
  const call = props.call;
  const [speakerOn, setSpeakerOn] = useState(true);
  const rtc = useCallRtcSession({
    resetKey: call?.id ?? "",
    previewEnabled: false,
    accessToken: props.access?.accessToken ?? "",
    side: "STAFF",
    iceServers: props.access?.iceServers ?? [],
    videoEnabled: false,
    onCallState: (state) => {
      if (call) props.onCallChange({ ...call, status: state.status as ApiCall["status"], endedBy: state.endedBy ?? null, durationSeconds: state.durationSeconds ?? null });
    },
  });
  const elapsed = useElapsed(call?.connectedAt ?? null, call?.status === "ACTIVE");
  const mode = resolveAudioMode(call, props.errorText, rtc.connectionPhase, rtc.mediaIssue);
  useLoopingAudio("/audio/ringtone.mp3", props.open && (mode === "incoming" || mode === "ringing"), 0.5);

  useEffect(() => {
    if (!props.open || !props.access || !call || rtc.connectionPhase !== "idle") return;
    if (call.status === "ACCEPTED" || call.status === "CONNECTING") void rtc.start();
  }, [props.open, props.access, call?.status, rtc.connectionPhase, rtc.start]);

  // Микрофон держим только пока оверлей открыт и звонок не завершён: терминал
  // приходит и поллингом состояния, а не только по RTC-сокету (VideoCallOverlay).
  useEffect(() => {
    if (!props.open || isTerminalCallStatus(call?.status)) rtc.stop();
  }, [props.open, call?.status, rtc.stop]);

  if (!props.dialog) return null;
  const channel = providerMeta[props.dialog.channel];
  const subCaption = mode === "active" ? (rtc.micOn ? "Говорите" : "Ваш микрофон выключен") : undefined;
  const builtStatus = buildAudioStatus(audioStatusKey(mode, call, props.errorText, rtc.connectionPhase, rtc.mediaIssue), props.dialog.name, call?.durationSeconds ?? undefined);
  const status = props.errorText && builtStatus
    ? { ...builtStatus, caption: props.errorText }
    : builtStatus;

  const onAccept = () => { void rtc.start(); };
  const finish = async () => {
    const token = props.access?.accessToken;
    if (!token || !call || isTerminalCallStatus(call.status)) return;
    try { props.onCallChange(await endCallByAccess(token)); }
    finally { rtc.stop(); }
  };
  const onEnd = () => { void finish(); };
  const endAndClose = async () => {
    if (mode === "active" || mode === "reconnecting" || mode === "connecting") await finish();
    props.onClose();
  };
  // retry для статус-экрана: при проблемах с устройствами/браузером — перепроверка,
  // иначе — пересоздание звонка (props.onRetry) или рестарт соединения.
  const onRetry = () => {
    if (rtc.mediaIssue === "devices" || rtc.mediaIssue === "unsupported") void rtc.prepare();
    else if (rtc.connectionPhase === "failed") void rtc.restart();
    else props.onRetry();
  };

  return (
    <Modal open={props.open} onCancel={() => void endAndClose()} footer={null} closable={false} width={428} className="call-modal audio-call-modal" destroyOnHidden>
      <AudioCallView
        mode={mode}
        status={status ?? undefined}
        peerName={props.dialog.name}
        peerInitials={props.dialog.initials}
        channelLabel={channel.label}
        showChannel
        micOn={rtc.micOn}
        speakerOn={speakerOn}
        remoteStream={rtc.remoteStream}
        remoteMicOn={rtc.remoteMicOn}
        elapsedSeconds={elapsed}
        durationSeconds={call?.durationSeconds ?? null}
        mediaIssue={rtc.mediaIssue}
        statusLabel={statusLabel(mode)}
        subCaption={subCaption}
        onToggleMic={rtc.toggleMic}
        onToggleSpeaker={() => setSpeakerOn((current) => !current)}
        onAccept={onAccept}
        onDecline={props.onCancel}
        onCancel={mode === "ringing" ? props.onCancel : () => void endAndClose()}
        onEnd={onEnd}
        onClose={() => void endAndClose()}
        onCallAgain={props.onRetry}
        onRetry={onRetry}
      />
    </Modal>
  );
}

function resolveAudioMode(call: ApiCall | null, errorText: string, connection: string, mediaIssue: string): AudioCallMode {
  if (errorText || !call) return "status";
  if (mediaIssue === "devices" || mediaIssue === "unsupported") return "status";
  // Звонок всегда инициирует оператор, поэтому до ответа клиента это исходящий.
  if (call.status === "REQUESTED" || call.status === "RINGING") return "ringing";
  if (call.status === "ACCEPTED") return connection === "connected" ? "active" : "connecting";
  if (connection === "reconnecting") return "reconnecting";
  if (connection === "failed") return "status";
  if (call.status === "ACTIVE" || connection === "connected") return "active";
  if (isTerminalCallStatus(call.status)) return "status";
  return "connecting";
}

// Ключ статуса, который buildAudioStatus умеет превратить в статус-центр.
function audioStatusKey(mode: AudioCallMode, call: ApiCall | null, errorText: string, connection: string, mediaIssue: string): string {
  if (errorText) return "FAILED";
  if (mediaIssue === "unsupported") return "unsupported";
  if (mediaIssue === "devices") return "nodevice";
  if (mode === "status") {
    if (connection === "failed") return "FAILED";
    return call?.status ?? "ENDED";
  }
  if (mode === "connecting" || mode === "reconnecting") return mode;
  return call?.status ?? "ENDED";
}

function statusLabel(mode: AudioCallMode): string {
  if (mode === "incoming") return "Входящий звонок";
  if (mode === "ringing") return "Исходящий звонок";
  if (mode === "active") return "Аудиозвонок";
  if (mode === "connecting") return "Соединение";
  if (mode === "reconnecting") return "Переподключение";
  return "";
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
