// Видеозвонок (клиент): видео-сцена страницы /calls/<invite>. Не делает bootstrap
// (он выполнен в CallApp) — переиспользует загруженные call/accessToken/iceServers,
// держит свой видео-RTC и поллинг состояния до терминала.

import { CallView, useCallRtcSession, useLoopingAudio } from "@chatballs/ui";
import { useCallback, useEffect, useMemo, useState } from "react";

import { acceptCall, declineCall, endCall, fetchCallState, type CallInfo } from "../api";
import { buildCallViewStatus, callViewSubtitle, isTerminalCall, resolveCallViewMode } from "./model";
import { useConnectionTimer } from "./useConnectionTimer";
import { t } from "../i18n";

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
  const [errorText, setErrorText] = useState("");

  const rtc = useCallRtcSession({
    resetKey: call?.callId ?? "",
    previewEnabled: Boolean(call && accessToken && !isTerminalCall(call.status) && !started),
    accessToken,
    side: "CUSTOMER",
    iceServers,
    onCallState: (state) => { if (call) onCall({ ...call, ...state }); },
  });
  const close = useCallback(async () => {
    if (accessToken && call && !isTerminalCall(call.status) && call.status !== "REQUESTED" && call.status !== "RINGING") {
      try { onCall(await endCall(accessToken)); } catch { /* terminal polling remains authoritative */ }
    }
    rtc.stop();
    if (history.length > 1) history.back(); else window.close();
  }, [accessToken, call, onCall, rtc.stop]);

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
    setErrorText("");
    try {
      const stream = await rtc.prepare();
      if (!stream) return;
      if (call?.status === "REQUESTED" || call?.status === "RINGING") {
        onCall(await acceptCall(accessToken));
      }
      setStarted(true);
      await rtc.start();
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("call.could_not_accept"));
    } finally {
      setJoining(false);
    }
  }

  async function cancelPrecall() {
    if (!accessToken) return;
    setErrorText("");
    try {
      const ended = call?.status === "REQUESTED" || call?.status === "RINGING"
        ? await declineCall(accessToken)
        : await endCall(accessToken);
      onCall(ended);
      rtc.stop();
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("call.could_not_end"));
    }
  }

  async function end() {
    if (!accessToken) return;
    try { onCall(await endCall(accessToken)); }
    catch (error) { setErrorText(error instanceof Error ? error.message : t("call.could_not_end")); }
    finally { rtc.stop(); }
  }

  const mode = resolveCallViewMode({ loading, invalid, call, started, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue, errorText });
  useLoopingAudio("/chat/audio/ringtone.mp3", !started && (call?.status === "REQUESTED" || call?.status === "RINGING"));
  const status = useMemo(
    () => buildCallViewStatus({ loading, invalid, call, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue, errorText, close: () => void close(), retry: rtc.restart, prepare: rtc.prepare, join: () => void join() }),
    [loading, invalid, call, joining, rtc.connectionPhase, rtc.mediaIssue, errorText, close, rtc.restart, rtc.prepare],
  );
  const elapsed = useConnectionTimer(rtc.connectionPhase === "connected");
  const peerName = call?.staffName || t("call.operator");
  const initials = peerName.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() || t("call.operator_initials");
  const mediaCaption = rtc.mediaIssue === "devices" ? t("call.no_camera_mic_access") : rtc.mediaIssue === "video" ? t("call.camera_unavailable") : t("call.camera_off");

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
        cancelLabel={t("call.decline")}
        onToggleMic={rtc.toggleMic}
        onToggleCam={rtc.toggleCam}
        onJoin={() => void join()}
        onCancel={() => void cancelPrecall()}
        onEnd={() => void end()}
        onClose={() => void close()}
      />
    </main>
  );
}
