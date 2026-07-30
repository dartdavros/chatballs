import { CallView, useCallRtcSession, useLoopingAudio } from "@edevs/ui";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  acceptCall,
  declineCall,
  fetchCallState,
  resolveCallInvite,
  type CallBootstrap,
  type CallInfo,
} from "../api";
import { AudioCallStage } from "./AudioCallStage";
import { buildCallViewStatus, callViewSubtitle, isTerminalCall, resolveCallViewMode } from "./model";

function storageKey() { return `edevs-call:${location.pathname}`; }
function inviteTokenFromPath() { return location.pathname.match(/\/calls\/([^/]+)/)?.[1] ?? ""; }
function accessTokenFromHash() { return location.hash.startsWith("#") ? location.hash.slice(1) : ""; }

export function CallApp() {
  const [loading, setLoading] = useState(true);
  const [invalid, setInvalid] = useState(false);
  const [call, setCall] = useState<CallInfo | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [iceServers, setIceServers] = useState<RTCIceServer[]>([]);
  const [started, setStarted] = useState(false);
  const [joining, setJoining] = useState(false);

  const rtc = useCallRtcSession({
    resetKey: call?.callId ?? "",
    previewEnabled: Boolean(call && accessToken && !isTerminalCall(call.status) && !started),
    accessToken,
    side: "CUSTOMER",
    iceServers,
    onCallState: (state) => setCall((current) => current ? { ...current, ...state } : state),
  });
  const close = useCallback(() => {
    if (started) rtc.end();
    if (history.length > 1) history.back(); else window.close();
  }, [rtc.end, started]);

  // Тип звонка определяется из приглашения/состояния. Все хуки выше вызваны до
  // условного return, поэтому их количество постоянно (rules of hooks). Аудио
  // рендерится AudioCallStage (своим RTC); видеопуть — ниже без изменений.
  if (call?.kind !== "VIDEO") {
    return <AudioCallStage call={call} accessToken={accessToken} iceServers={iceServers} loading={loading} invalid={invalid} onCall={setCall} />;
  }

  const applyBootstrap = useCallback((value: CallBootstrap) => {
    sessionStorage.setItem(storageKey(), value.accessToken);
    setAccessToken(value.accessToken);
    setIceServers(value.iceServers ?? []);
    setCall(value.call);
    setLoading(false);
  }, []);

  useEffect(() => {
    const fromHash = accessTokenFromHash();
    const saved = sessionStorage.getItem(storageKey());
    if (fromHash) history.replaceState(null, "", location.pathname);
    const token = fromHash || saved || "";
    if (token) {
      setAccessToken(token);
      void fetchCallState(token).then((result) => {
        if (!result) { setInvalid(true); setLoading(false); return; }
        setCall(result.call);
        setIceServers(result.iceServers ?? []);
        setLoading(false);
      });
      return;
    }
    const invite = inviteTokenFromPath();
    if (!invite) { setInvalid(true); setLoading(false); return; }
    void resolveCallInvite(invite).then((result) => {
      if (!result) { setInvalid(true); setLoading(false); return; }
      applyBootstrap(result);
    });
  }, [applyBootstrap]);

  useEffect(() => {
    if (!accessToken || !call || isTerminalCall(call.status)) return;
    const timer = setInterval(async () => {
      const result = await fetchCallState(accessToken);
      if (result) {
        setCall(result.call);
        if (result.iceServers) setIceServers(result.iceServers);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [accessToken, call?.status]);

  useEffect(() => {
    if (isTerminalCall(call?.status)) rtc.stop();
  }, [call?.status, rtc.stop]);

  async function join() {
    if (!accessToken || joining) return;
    setJoining(true);
    if (call?.status === "REQUESTED" || call?.status === "RINGING") {
      const accepted = await acceptCall(accessToken);
      if (accepted) setCall(accepted);
    }
    setStarted(true);
    rtc.start();
    setJoining(false);
  }

  async function cancelPrecall() {
    if (!accessToken) return;
    if (call?.status === "REQUESTED" || call?.status === "RINGING") {
      const declined = await declineCall(accessToken);
      if (declined) setCall(declined);
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

function useConnectionTimer(active: boolean) {
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) return;
    const origin = startedAt ?? Date.now();
    if (startedAt == null) setStartedAt(origin);
    const update = () => setSeconds(Math.floor((Date.now() - origin) / 1000));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [active, startedAt]);
  return seconds;
}
