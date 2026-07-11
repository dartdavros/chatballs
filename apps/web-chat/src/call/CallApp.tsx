import { useCallback, useEffect, useRef, useState } from "react";

import { acceptCall, declineCall, fetchCallState, resolveCallInvite, type CallInfo } from "../api";

// Клиентская страница звонка /calls/<invite-token> (SPEC-HUB-0013 §7.2, DG-07).
// Верстка и состояния — по baseline «# UI для онлайн звонка/Экран звонка.dc.html»
// (сторона «Клиент»). Медиасоединение WebRTC подключается следующим этапом:
// после принятия страница показывает состояние «Соединяем звонок».
//
// Token проверяется ДО запроса камеры и микрофона (§7.2). Access token живёт
// в sessionStorage вкладки — перезагрузка не «сжигает» одноразовый invite.

type Phase =
  | "loading"
  | "invalid"
  | "precall"
  | "connecting"
  | "declined"
  | "cancelled"
  | "missed"
  | "expired"
  | "ended"
  | "failed";

const TERMINAL_BY_STATUS: Record<string, Phase> = {
  DECLINED: "declined",
  CANCELLED: "cancelled",
  MISSED: "missed",
  EXPIRED: "expired",
  ENDED: "ended",
  FAILED: "failed",
};

const STATUS_VIEW: Record<string, { icon: "spinner" | "alert" | "declined" | "missed" | "clock"; tone: "neutral" | "error" | "warn"; title: string; caption: string }> = {
  loading: { icon: "spinner", tone: "neutral", title: "Проверяем приглашение", caption: "Секунду…" },
  invalid: { icon: "clock", tone: "warn", title: "Приглашение недействительно", caption: "Ссылка устарела или уже была использована. Запросите новое приглашение в чате." },
  connecting: { icon: "spinner", tone: "neutral", title: "Соединяем звонок", caption: "Устанавливаем защищённое соединение…" },
  declined: { icon: "declined", tone: "neutral", title: "Звонок отклонён", caption: "Вы отклонили вызов. Продолжить общение можно в чате." },
  cancelled: { icon: "declined", tone: "neutral", title: "Звонок отменён", caption: "Сотрудник отменил приглашение. Продолжить общение можно в чате." },
  missed: { icon: "missed", tone: "warn", title: "Пропущенный звонок", caption: "Никто не ответил вовремя. Запросите новое приглашение в чате." },
  expired: { icon: "clock", tone: "warn", title: "Время ожидания истекло", caption: "Приглашение истекло. Запросите новое приглашение в чате." },
  ended: { icon: "declined", tone: "neutral", title: "Звонок завершён", caption: "Спасибо! Продолжить общение можно в чате." },
  failed: { icon: "alert", tone: "error", title: "Не удалось соединиться", caption: "Проверьте интернет-соединение и попробуйте снова по ссылке из чата." },
};

function storageKey(): string {
  return `edevs-call:${location.pathname}`;
}

function inviteTokenFromPath(): string {
  const match = location.pathname.match(/\/calls\/([^/]+)/);
  return match ? match[1] : "";
}

function accessTokenFromHash(): string {
  return location.hash.startsWith("#") ? location.hash.slice(1) : "";
}

export function CallApp() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [call, setCall] = useState<CallInfo | null>(null);
  const [accessToken, setAccessToken] = useState<string>("");
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [mediaError, setMediaError] = useState(false);
  const [joining, setJoining] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const stopMedia = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const applyCall = useCallback((info: CallInfo | null) => {
    if (!info) return;
    setCall(info);
    const terminal = TERMINAL_BY_STATUS[info.status];
    if (terminal) {
      setPhase(terminal);
      stopMedia();
    } else if (info.status === "ACCEPTED" || info.status === "CONNECTING") {
      setPhase("connecting");
    }
  }, [stopMedia]);

  // Вход: access token из fragment (Web Chat) или invite token из пути (TG/MAX).
  useEffect(() => {
    const saved = sessionStorage.getItem(storageKey());
    const fromHash = accessTokenFromHash();
    if (fromHash) {
      sessionStorage.setItem(storageKey(), fromHash);
      history.replaceState(null, "", location.pathname); // token не остаётся в адресе
    }
    const token = fromHash || saved || "";
    if (token) {
      setAccessToken(token);
      void fetchCallState(token).then((info) => {
        if (!info) { setPhase("invalid"); return; }
        setPhase("precall");
        applyCall(info);
      });
      return;
    }
    const invite = inviteTokenFromPath();
    if (!invite) { setPhase("invalid"); return; }
    void resolveCallInvite(invite).then((resolved) => {
      if (!resolved) { setPhase("invalid"); return; }
      sessionStorage.setItem(storageKey(), resolved.accessToken);
      setAccessToken(resolved.accessToken);
      setPhase("precall");
      applyCall(resolved.call);
    });
  }, [applyCall]);

  // Поллинг состояния: отмена сотрудником и таймауты приходят с сервера.
  useEffect(() => {
    if (!accessToken || phase === "invalid" || TERMINAL_BY_STATUS[call?.status ?? ""]) return;
    const timer = setInterval(async () => {
      const info = await fetchCallState(accessToken);
      if (info) applyCall(info);
    }, 2000);
    return () => clearInterval(timer);
  }, [accessToken, phase, call?.status, applyCall]);

  // Pre-call preview: камера/микрофон запрашиваются только после проверки token.
  useEffect(() => {
    if (phase !== "precall") return;
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        setMediaError(false);
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => { if (!cancelled) setMediaError(true); });
    return () => { cancelled = true; };
  }, [phase]);

  useEffect(() => () => stopMedia(), [stopMedia]);

  // Mute/выключение камеры — track.enabled, без пересоздания потока (§10).
  useEffect(() => {
    streamRef.current?.getAudioTracks().forEach((t) => { t.enabled = micOn; });
  }, [micOn]);
  useEffect(() => {
    streamRef.current?.getVideoTracks().forEach((t) => { t.enabled = camOn; });
    if (camOn && videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  }, [camOn]);

  async function join() {
    if (!accessToken || joining) return;
    setJoining(true);
    const info = await acceptCall(accessToken);
    setJoining(false);
    if (info) applyCall(info);
  }

  async function decline() {
    if (!accessToken) return;
    const info = await declineCall(accessToken);
    if (info) applyCall(info);
    else setPhase("declined");
  }

  const staffName = call?.staffName || "Оператор";
  const initials = staffName.trim().split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase() || "ОП";
  const showVideo = phase === "precall" && camOn && !mediaError;
  const status = phase === "precall" ? null : STATUS_VIEW[phase];
  const subtitle = phase === "precall" ? "Проверьте камеру и микрофон" : status?.title ?? "";

  return (
    <div style={{ minHeight: "100vh", boxSizing: "border-box", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, background: "#f5f6f8", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif", color: "#262626" }}>
      <div style={{ width: "100%", maxWidth: 428, background: "#fff", border: "1px solid #e8e8e8", borderRadius: 24, boxShadow: "0 12px 40px rgba(0,0,0,0.12)", overflow: "hidden" }}>

        <div style={{ display: "flex", alignItems: "center", gap: 11, padding: "12px 15px", borderBottom: "1px solid #e8e8e8" }}>
          <div style={{ width: 38, height: 38, borderRadius: "50%", background: "#1677ff", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 600, flex: "none" }}>{initials}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#1f1f1f", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{staffName}</span>
            <span style={{ fontSize: 12, color: "#8c8c8c" }}>{subtitle}</span>
          </div>
        </div>

        <div style={{ position: "relative", aspectRatio: "16/9", background: "#141414", overflow: "hidden" }}>
          <video ref={videoRef} autoPlay muted playsInline style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", display: showVideo ? "block" : "none", transform: "scaleX(-1)" }} />

          {phase === "precall" && !showVideo && (
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16 }}>
              <div style={{ width: 88, height: 88, borderRadius: "50%", background: "#595959", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 30, fontWeight: 600, boxShadow: "0 4px 18px rgba(0,0,0,.35)" }}>ВЫ</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#fff" }}>Вы</div>
                <div style={{ fontSize: 12.5, color: "rgba(255,255,255,.6)", marginTop: 3 }}>{mediaError ? "Нет доступа к камере и микрофону" : "Камера выключена"}</div>
              </div>
            </div>
          )}

          {status && (
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: "22px 26px", textAlign: "center", background: "#1a1a1a" }}>
              <StatusIcon name={status.icon} tone={status.tone} />
              <div>
                <div style={{ fontSize: 15.5, fontWeight: 600, color: "#fff", lineHeight: 1.3 }}>{status.title}</div>
                <div style={{ fontSize: 12.5, color: "rgba(255,255,255,.6)", marginTop: 6, lineHeight: 1.5, maxWidth: 280 }}>
                  {phase === "ended" && call?.durationSeconds != null
                    ? `Длительность ${fmtDuration(call.durationSeconds)}. ${status.caption}`
                    : status.caption}
                </div>
              </div>
            </div>
          )}
        </div>

        {phase === "precall" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 15, padding: "16px 16px 18px" }}>
            <div style={{ display: "flex", justifyContent: "center", gap: 32 }}>
              <ToggleControl label="Микрофон" on={micOn} disabled={mediaError} onClick={() => setMicOn((v) => !v)} kind="mic" />
              <ToggleControl label="Камера" on={camOn} disabled={mediaError} onClick={() => setCamOn((v) => !v)} kind="cam" />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={() => void decline()} style={{ flex: 1, height: 44, borderRadius: 12, border: "1px solid #d9d9d9", background: "#fff", color: "#262626", fontSize: 14, fontWeight: 600, fontFamily: "inherit", cursor: "pointer" }}>Отклонить</button>
              <button onClick={() => void join()} disabled={joining} style={{ flex: 1, height: 44, borderRadius: 12, border: "none", background: "#1677ff", color: "#fff", fontSize: 14, fontWeight: 600, fontFamily: "inherit", cursor: "pointer", boxShadow: "0 2px 8px rgba(22,119,255,.35)" }}>{joining ? "Подключение…" : "Присоединиться"}</button>
            </div>
            {mediaError && (
              <div style={{ fontSize: 12, color: "#8c8c8c", textAlign: "center", lineHeight: 1.5 }}>
                Разрешите доступ к камере и микрофону в настройках браузера — или присоединяйтесь без видео.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function fmtDuration(seconds: number): string {
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function ToggleControl({ label, on, disabled, onClick, kind }: { label: string; on: boolean; disabled?: boolean; onClick: () => void; kind: "mic" | "cam" }) {
  const style = on
    ? { border: "1px solid #d9d9d9", background: "#f5f5f5", color: "#434343" }
    : { border: "1px solid #ffccc7", background: "#fff2f0", color: "#cf1322" };
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <button onClick={onClick} disabled={disabled} aria-label={label} style={{ width: 54, height: 54, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", cursor: disabled ? "default" : "pointer", flex: "none", opacity: disabled ? 0.5 : 1, ...style }}>
        <DeviceIcon kind={kind} on={on} />
      </button>
      <span style={{ fontSize: 12, color: "#8c8c8c" }}>{label}</span>
    </div>
  );
}

function DeviceIcon({ kind, on }: { kind: "mic" | "cam"; on: boolean }) {
  const common = { viewBox: "0 0 24 24", width: 22, height: 22, fill: "none", stroke: "currentColor", strokeWidth: 1.85, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (kind === "mic") {
    return on
      ? <svg {...common}><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M19 10v1a7 7 0 0 1-14 0v-1" /><line x1="12" y1="18" x2="12" y2="22" /></svg>
      : <svg {...common}><line x1="3" y1="3" x2="21" y2="21" /><path d="M9 9v2a3 3 0 0 0 5.1 2.1" /><path d="M15 9.3V5a3 3 0 0 0-5.9-.7" /><path d="M19 10v1a7 7 0 0 1-1.4 4.2M12 18a7 7 0 0 1-7-7v-1" /><line x1="12" y1="18" x2="12" y2="22" /></svg>;
  }
  return on
    ? <svg {...common}><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2.5" /></svg>
    : <svg {...common}><line x1="2" y1="2" x2="22" y2="22" /><path d="M16 16v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" /><path d="M10 5h4a2 2 0 0 1 2 2v3l4-3v9" /></svg>;
}

function StatusIcon({ name, tone }: { name: "spinner" | "alert" | "declined" | "missed" | "clock"; tone: "neutral" | "error" | "warn" }) {
  const tones = {
    neutral: { bg: "rgba(255,255,255,.08)", fg: "#fff" },
    error: { bg: "rgba(255,77,79,.16)", fg: "#ff7875" },
    warn: { bg: "rgba(250,173,20,.16)", fg: "#ffc53d" },
  }[tone];
  const common = { viewBox: "0 0 24 24", width: 26, height: 26, fill: "none", stroke: "currentColor", strokeWidth: 1.9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const icons = {
    spinner: <svg {...common} strokeWidth={2} style={{ animation: "edvSpin .9s linear infinite" }}><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>,
    alert: <svg {...common}><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>,
    declined: <svg {...common}><path transform="rotate(135 12 12)" d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>,
    missed: <svg {...common}><path d="M23 7l-8 8-4-4-9 9" /><polyline points="17 7 23 7 23 13" /></svg>,
    clock: <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>,
  };
  return (
    <div style={{ width: 56, height: 56, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: tones.bg, color: tones.fg }}>
      {icons[name]}
    </div>
  );
}
