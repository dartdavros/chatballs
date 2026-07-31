// Аудиозвонок (клиент): audio-сцена страницы /calls/<invite>. Не делает bootstrap
// (он выполнен в CallApp) — переиспользует загруженные call/accessToken/iceServers,
// держит свой аудио-RTC (videoEnabled:false) и поллинг состояния до терминала.

import { AudioCallView, type AudioCallMode, type AudioCallStatus, useCallRtcSession, useLoopingAudio } from "@edevs/ui";
import { useCallback, useEffect, useMemo, useState } from "react";

import { acceptCall, declineCall, fetchCallState, type CallInfo } from "../api";
import { audioCallStatusLabel, buildAudioCallViewStatus, isTerminalCall, resolveAudioCallViewMode } from "./model";
import { useConnectionTimer } from "./useConnectionTimer";

type Props = {
  call: CallInfo | null;
  accessToken: string;
  iceServers: RTCIceServer[];
  loading: boolean;
  invalid: boolean;
  onCall: (call: CallInfo) => void;
};

export function AudioCallStage({ call, accessToken, iceServers, loading, invalid, onCall }: Props) {
  const [started, setStarted] = useState(false);
  const [joining, setJoining] = useState(false);

  const rtc = useCallRtcSession({
    resetKey: call?.callId ?? "",
    previewEnabled: false,
    accessToken,
    side: "CUSTOMER",
    iceServers,
    videoEnabled: false,
    onCallState: (state) => { if (call) onCall({ ...call, ...state }); },
  });

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

  const close = useCallback(() => {
    if (started) rtc.end();
    if (history.length > 1) history.back(); else window.close();
  }, [rtc.end, started]);

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

  const onCancel = useCallback(async () => {
    if (!accessToken) return;
    if (call?.status === "REQUESTED" || call?.status === "RINGING") {
      const declined = await declineCall(accessToken);
      if (declined) onCall(declined);
      return;
    }
    setStarted(true);
    if (rtc.start()) rtc.end();
  }, [accessToken, call?.status, onCall, rtc]);

  const mode: AudioCallMode = resolveAudioCallViewMode({ loading, invalid, call, started, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue });
  useLoopingAudio("/chat/audio/ringtone.mp3", !started && (call?.status === "REQUESTED" || call?.status === "RINGING"));
  const status: AudioCallStatus | undefined = useMemo(
    () => buildAudioCallViewStatus({ loading, invalid, call, connection: rtc.connectionPhase, mediaIssue: rtc.mediaIssue, close }),
    [loading, invalid, call, rtc.connectionPhase, rtc.mediaIssue, close],
  );
  const elapsed = useConnectionTimer(rtc.connectionPhase === "connected");
  const peerName = call?.staffName || "Оператор";
  const initials = peerName.trim().split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() || "ОП";

  return (
    <main className="public-call-page">
      <AudioCallView
        mode={mode}
        status={status}
        peerName={peerName}
        peerInitials={initials}
        micOn={rtc.micOn}
        speakerOn
        remoteStream={rtc.remoteStream}
        remoteMicOn={rtc.remoteMicOn}
        elapsedSeconds={elapsed}
        durationSeconds={call?.durationSeconds ?? null}
        mediaIssue={rtc.mediaIssue}
        statusLabel={audioCallStatusLabel(mode, status)}
        subCaption={mode === "active" ? (rtc.micOn ? "Говорите" : "Ваш микрофон выключен") : undefined}
        onToggleMic={rtc.toggleMic}
        onAccept={() => void join()}
        onDecline={() => void onCancel()}
        onCancel={() => void onCancel()}
        onEnd={rtc.end}
        onClose={close}
      />
    </main>
  );
}
