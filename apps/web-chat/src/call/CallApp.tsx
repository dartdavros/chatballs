// Страница звонка /calls/<invite>: bootstrap (invite token / access token из
// ссылок TG/MAX или session-storage) и поллинг состояния, затем диспетчер по типу
// звонка — VIDEO → VideoCallStage, иначе → AudioCallStage (default AUDIO).
//
// Composition-only: RTC, UI-сцена и таймер живут в Stage-компонентах. Здесь только
// загрузка данных звонка и роутинг по kind. Все хуки вызваны безусловно — правила
// хуков соблюдены, ветвление только в JSX (ранних return из середины тела нет).

import { useCallback, useEffect, useState } from "react";

import {
  fetchCallState,
  isVideoCall,
  resolveCallInvite,
  type CallBootstrap,
  type CallInfo,
} from "../api";
import { AudioCallStage } from "./AudioCallStage";
import { VideoCallStage } from "./VideoCallStage";

function storageKey() { return `edevs-call:${location.pathname}`; }
function inviteTokenFromPath() { return location.pathname.match(/\/calls\/([^/]+)/)?.[1] ?? ""; }
function accessTokenFromHash() { return location.hash.startsWith("#") ? location.hash.slice(1) : ""; }

export function CallApp() {
  const [loading, setLoading] = useState(true);
  const [invalid, setInvalid] = useState(false);
  const [call, setCall] = useState<CallInfo | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [iceServers, setIceServers] = useState<RTCIceServer[]>([]);

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

  return isVideoCall(call)
    ? <VideoCallStage call={call} accessToken={accessToken} iceServers={iceServers} loading={loading} invalid={invalid} onCall={setCall} />
    : <AudioCallStage call={call} accessToken={accessToken} iceServers={iceServers} loading={loading} invalid={invalid} onCall={setCall} />;
}
