// Видеозвонок (клиент): видео-сцена страницы /calls/<invite>. Не делает bootstrap
// (он выполнен в CallApp) — переиспользует загруженные call/accessToken/iceServers,
// держит свой видео-RTC и поллинг состояния до терминала.

import { CallView, useCallRtcSession, useLoopingAudio } from "@edevs/ui";
import { useCallback, useEffect, useMemo, useState } from "react";

import { acceptCall, declineCall, fetchCallState, type CallInfo } from "../api";
import { buildCallViewStatus, callViewSubtitle, isTerminalCall, resolveCallViewMode } from "./model";
import { useConnectionTimer } from "./useConnectionTimer";

type Props = {
  call: CallInfo | null;
  accessToken: string;
  iceServers: RTCIceServer[];
  loading: boolean;
  invalid: boolean;
  onCall: (call: CallInfo) => void;
};

export function VideoCallStage({ call, accessToken, iceServers, loading, invalid, onCall }: Props) {
  const [started, setStarted] = useState(false);
  const [joining, setJoining] = useState(false);

  const rtc = useCallRtcSession({
    resetKey: call?.callId ?? "",
    previewEnabled: Boolean(call && accessToken && !isTerminalCall(call.status) && !started),
    accessToken,
    side: "CUSTOMER",
    iceServers,
    onCallState: (state) => { if (call) onCall({ ...call, ...state }); else onCall(state); },
  });
  const close = useCallback(() => {
    if (started) rtc.end();
    if (history.length > 1) history.back(); else window.close();
  }, [rtc.end, started]);

  // Поллинг состояния до терминала.
  useEffect(() => {
    if (!accessToken || !call || isTerminalCall(call.status)) return;
    const timer = setInterval(async () => {
      const result = await fetchCallState(accessToken);
      if (result) onCall(result.call);
    }, 2000);
    return () => clearInterval(timer);
  }, [accessToken, call?.status, onCall]);

  useEffect(() => {
    if (isTerminalCall(call?.status)) rtc.stop();
  }, [call?.status, rtc.stop]);

  async function join() {
    if (!accessToken || joining) return;
    setJoining(true);
    if (call?.status === "REQUESTED" || call?.status === "RINGING") {
      const accepted = await acceptCall(accessToken);
      if (accepted) onCall(accepted);
    }
    setStarted(true);
    rtc.start();
    setJoining(false);
  }

  async function cancelPrecall() {
    if (!accessToken) return;
    if (call?.status === "REQUESTED" || call?.status === "RINGING") {
      const declined = await declineCall(accessToken);
      if (declined) onCall(declined);
      return;
    }
    setStarted(true);
    if (rtc.start()) rtc.end();
  }

  const mode = resolveCallViewMode({ loading, invalid, call, started, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue });
  useLoopingAudio("/chat/audio/ringtone.mp3", !started && (call?.status === "REQUESTED" || call?.status === "RINGING"));
  const status = useMemo(
    () => buildCallViewStatus({ loading, invalid, call, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue, close, retry: rtc.restart, prepare: rtc.prepare, join: () => void join() }),
    [loading, invalid, call, joining, rtc.connectionPhase, rtc.mediaIssue, close, rtc.restart, rtc.prepare],
  );
  const elapsed = useConnectionTimer(rtc.connectionPhase === "connected");
  const peerName = call?.staffName || "Оператор";
  const initials = peerName.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() || "ОП";
  const mediaCaption = rtc.mediaIssue === "devices" ? "Нет доступа к камере и микрофону" : rtc.mediaIssue === "video" ? "Камера недоступна" : "Камера выключена";

  return (
    <main className="public-call-page">
      <CallView
        mode={mode}
        peerName={peerName}
        peerInitials={initials}
        subtitle={callViewSubtitle(mode, status)}
        localStream={rtc.localStream}
        remoteStream={rtc.remoteStream}
        micOn={rtc.micOn}
        camOn={rtc.camOn}
        remoteMicOn={rtc.remoteMicOn}
        remoteCamOn={rtc.remoteCamOn}
        mediaCaption={mediaCaption}
        elapsedSeconds={elapsed}
        status={status}
        joining={joining || rtc.preparing}
        cancelLabel="Отклонить"
        onToggleMic={rtc.toggleMic}
        onToggleCam={rtc.toggleCam}
        onJoin={() => void join()}
        onCancel={() => void cancelPrecall()}
        onEnd={rtc.end}
        onClose={close}
      />
    </main>
  );
}
