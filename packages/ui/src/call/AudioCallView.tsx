// Аудиозвонок — полноэкранный портретный UI (baseline «Аудиозвонок.dc.html»).
// Тёмный градиент 150deg #0958d9→#722ed1→#c41d7f + два дрейфующих блоба,
// glass-аватар 126px с двумя волнами edv-ring2, живая осциллограмма собеседника.
// Никакой камеры/видео/PiP — это честный аудио-режим.

import { useEffect, useRef } from "react";

import { AudioCallWaveform } from "./AudioCallWaveform";
import { AudioStatusIcon } from "./AudioCallIcons";
import { MicIcon, PhoneIcon, SpeakerIcon } from "./AudioCallIcons";
import { type AudioCallMode, type AudioCallStatus, formatDuration } from "./audioCallStates";
import "./audio-call.css";
import { t } from "../i18n";

type Props = {
  mode: AudioCallMode;
  status?: AudioCallStatus;
  peerName: string;
  peerInitials: string;
  channelLabel?: string;
  showChannel?: boolean;
  micOn?: boolean;
  speakerOn?: boolean;
  remoteStream?: MediaStream | null;
  remoteMicOn?: boolean;
  elapsedSeconds?: number;
  durationSeconds?: number | null;
  mediaIssue?: string;
  statusLabel?: string;
  subCaption?: string;
  onToggleMic?: () => void;
  onToggleSpeaker?: () => void;
  onAccept?: () => void;
  onDecline?: () => void;
  onCancel?: () => void;
  onEnd?: () => void;
  onClose?: () => void;
  onCallAgain?: () => void;
  onRetry?: () => void;
};

export function AudioCallView(props: Props) {
  const status = props.status;
  const isStatus = props.mode === "status" && !!status;
  const showAvatarCenter = !isStatus;
  const ringsVisible = props.mode === "incoming" || props.mode === "ringing";
  const isActive = props.mode === "active";
  const timer = formatDuration(props.elapsedSeconds ?? 0);

  return (
    <div className="hub-audio-view" data-bg={bgState(props.mode)}>
      <RemoteAudio stream={props.remoteStream} muted={props.speakerOn === false} />
      <div className="hub-audio-bg" aria-hidden>
        <div className="hub-audio-grad" />
        <div className="hub-audio-blob a" />
        <div className="hub-audio-blob b" />
        <div className="hub-audio-veil" />
      </div>

      <div className="hub-audio-body">
        <div className="hub-audio-top">
          <span className="hub-audio-status-label">{props.statusLabel ?? defaultStatusLabel(props.mode, status)}</span>
          {props.showChannel !== false && props.channelLabel && <span className="hub-audio-channel">{props.channelLabel}</span>}
          <div className="hub-audio-top-spacer" />
          {isActive && <span className="hub-audio-timer">{timer}</span>}
        </div>

        <div className="hub-audio-center">
          {showAvatarCenter && (
            <>
              <div className="hub-audio-avatar-wrap">
                {ringsVisible && (
                  <>
                    <i className="hub-audio-ring" />
                    <i className="hub-audio-ring delay" />
                  </>
                )}
                <div className="hub-audio-avatar">{props.peerInitials}</div>
              </div>
              <div className="hub-audio-name-block">
                <div className="hub-audio-name">{props.peerName}</div>
                <div className="hub-audio-sub">{props.subCaption ?? defaultSubCaption(props.mode, props.micOn)}</div>
              </div>
              <div className="hub-audio-wave-slot">
                {isActive && <AudioCallWaveform stream={props.remoteStream} micOn={props.remoteMicOn !== false} active />}
                {!isActive && durationPill(props.durationSeconds)}
              </div>
            </>
          )}
          {isStatus && status && (
            <StatusCenter status={status} />
          )}
        </div>

        <div className="hub-audio-bottom">
          {props.mode === "incoming" && (
            <PairBar left={{ label: t("call.decline"), tone: "decline", icon: <PhoneIcon rotated /> }} right={{ label: t("call.accept"), tone: "accept", icon: <PhoneIcon /> }} onLeft={props.onDecline} onRight={props.onAccept} />
          )}
          {props.mode === "ringing" && (
            <SingleRoundBar label={t("call.cancel_call")} tone="decline" icon={<PhoneIcon rotated />} onClick={props.onCancel ?? props.onEnd} />
          )}
          {props.mode === "connecting" && (
            <SingleRoundBar label={t("call.cancel_call")} tone="decline" icon={<PhoneIcon rotated />} onClick={props.onCancel ?? props.onEnd} />
          )}
          {props.mode === "reconnecting" && (
            <SingleRoundBar label={t("call.end")} tone="decline" icon={<PhoneIcon rotated />} onClick={props.onEnd} />
          )}
          {isActive && (
            <div className="hub-audio-active">
              <div className="hub-audio-device-row">
                <DeviceControl label={t("call.mic")} icon={<MicIcon on={props.micOn !== false} />} on={props.micOn !== false} onClick={props.onToggleMic} />
                <DeviceControl label={t("call.speaker")} icon={<SpeakerIcon on={props.speakerOn !== false} />} on={props.speakerOn !== false} onClick={props.onToggleSpeaker} />
              </div>
              <SingleRoundBar label={t("call.end")} tone="decline" icon={<PhoneIcon rotated />} onClick={props.onEnd} />
            </div>
          )}
          {isStatus && status && (
            <StatusBar status={status} onClose={props.onClose} onCallAgain={props.onCallAgain} onRetry={props.onRetry} onEnd={props.onEnd} />
          )}
        </div>
      </div>
    </div>
  );
}

function RemoteAudio({ stream, muted }: { stream?: MediaStream | null; muted: boolean }) {
  const ref = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const audio = ref.current;
    if (!audio) return;
    audio.srcObject = stream ?? null;
    if (stream) void audio.play().catch(() => undefined);
  }, [stream]);
  return <audio ref={ref} autoPlay muted={muted} className="hub-audio-remote" />;
}

function StatusCenter({ status }: { status: AudioCallStatus }) {
  return (
    <div className="hub-audio-status-center">
      <span className={`hub-audio-status-tile ${status.tone}`}><AudioStatusIcon name={status.icon} /></span>
      <div>
        <div className="hub-audio-status-title">{status.title}</div>
        <div className="hub-audio-status-caption">{status.caption}</div>
      </div>
    </div>
  );
}

function DeviceControl({ label, icon, on, onClick }: { label: string; icon: React.ReactNode; on: boolean; onClick?: () => void }) {
  return (
    <div className="hub-audio-device-control">
      <button className={`hub-audio-device${on ? "" : " off"}`} onClick={onClick} aria-label={label}>{icon}</button>
      <span>{label}</span>
    </div>
  );
}

function SingleRoundBar({ label, tone, icon, onClick }: { label: string; tone: "decline"; icon: React.ReactNode; onClick?: () => void }) {
  return (
    <div className="hub-audio-round-stack">
      <button className={`hub-audio-round ${tone}`} onClick={onClick} aria-label={label}>{icon}</button>
      <span className="hub-audio-round-label">{label}</span>
    </div>
  );
}

function PairBar({ left, right, onLeft, onRight }: { left: BarEnd; right: BarEnd; onLeft?: () => void; onRight?: () => void }) {
  return (
    <div className="hub-audio-pair">
      <EndStack end={left} onClick={onLeft} />
      <EndStack end={right} onClick={onRight} />
    </div>
  );
}

type BarEnd = { label: string; tone: "decline" | "accept"; icon: React.ReactNode };
function EndStack({ end, onClick }: { end: BarEnd; onClick?: () => void }) {
  return (
    <div className="hub-audio-round-stack">
      <button className={`hub-audio-round ${end.tone}`} onClick={onClick} aria-label={end.label}>{end.icon}</button>
      <span className="hub-audio-round-label">{end.label}</span>
    </div>
  );
}

// Бар для терминальных/ошибочных статусов: кнопки 48px, как в дизайне ended.
function StatusBar({ status, onClose, onCallAgain, onRetry, onEnd }: { status: AudioCallStatus; onClose?: () => void; onCallAgain?: () => void; onRetry?: () => void; onEnd?: () => void }) {
  const bar = status.bar;
  if (bar === "reconnect") {
    return <SingleRoundBar label={t("call.end")} tone="decline" icon={<PhoneIcon rotated />} onClick={onEnd} />;
  }
  if (bar === "close") {
    return (
      <div className="hub-audio-pill-bar">
        <PillButton kind="ghost" onClick={onClose}>{t("call.close")}</PillButton>
      </div>
    );
  }
  if (bar === "retrySingle") {
    return (
      <div className="hub-audio-pill-bar">
        <PillButton kind="solid" onClick={onCallAgain}>{t("call.call_again")}</PillButton>
      </div>
    );
  }
  if (bar === "retryClose") {
    return (
      <div className="hub-audio-pill-bar two">
        <PillButton kind="ghost" onClick={onClose}>{t("call.close")}</PillButton>
        <PillButton kind="solid" onClick={onRetry}>{t("call.retry")}</PillButton>
      </div>
    );
  }
  if (bar === "retryCheck") {
    return (
      <div className="hub-audio-pill-bar two">
        <PillButton kind="ghost" onClick={onClose}>{t("call.close")}</PillButton>
        <PillButton kind="solid" onClick={onRetry}>{t("call.retry_check")}</PillButton>
      </div>
    );
  }
  // ended / connecting
  return (
    <div className="hub-audio-pill-bar two">
      <PillButton kind="ghost" onClick={onClose}>{t("call.close")}</PillButton>
      <PillButton kind="solid" onClick={onCallAgain}>{t("call.call_again")}</PillButton>
    </div>
  );
}

function PillButton({ kind, onClick, children }: { kind: "solid" | "ghost"; onClick?: () => void; children: React.ReactNode }) {
  return <button className={`hub-audio-pill ${kind}`} onClick={onClick}>{children}</button>;
}

function durationPill(duration?: number | null) {
  if (duration == null || duration <= 0) return null;
  return (
    <div className="hub-audio-duration-pill">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
      {t("call.duration", { duration: formatDuration(duration) })}
    </div>
  );
}

function bgState(mode: AudioCallMode): string {
  if (mode === "active") return "active";
  if (mode === "status" || mode === "reconnecting") return "dim";
  return "full";
}

function defaultStatusLabel(mode: AudioCallMode, status?: AudioCallStatus): string {
  if (status) return status.title;
  if (mode === "incoming") return t("call.incoming");
  if (mode === "ringing") return t("call.outgoing");
  if (mode === "active") return t("call.audio_call");
  if (mode === "connecting") return t("call.connecting_status");
  if (mode === "reconnecting") return t("call.reconnecting");
  return t("call.call_ended");
}

function defaultSubCaption(mode: AudioCallMode, micOn?: boolean): string {
  if (mode === "active") return micOn ? t("call.speak") : t("call.mic_off");
  if (mode === "incoming" || mode === "ringing") return "";
  return "";
}
