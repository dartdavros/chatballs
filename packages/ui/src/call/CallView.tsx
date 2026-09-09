import { useEffect, useRef, useState, type ReactNode } from "react";

import { CloseIcon, DeviceIcon, FullscreenIcon, PhoneIcon, SpinnerIcon, StatusIcon, type StatusIconName } from "./CallIcons";
import "./call-view.css";
import { t } from "../i18n";

export type CallViewMode = "ringing" | "precall" | "connecting" | "active" | "reconnecting" | "status";

export type CallViewStatus = {
  icon: StatusIconName;
  tone: "neutral" | "error" | "warn";
  title: string;
  caption: string;
  actions?: Array<{ label: string; kind: "primary" | "secondary"; onClick: () => void }>;
};

type Props = {
  mode: CallViewMode;
  peerName: string;
  peerInitials: string;
  peerAvatarColor?: string;
  subtitle: string;
  channelBadge?: ReactNode;
  localStream?: MediaStream | null;
  remoteStream?: MediaStream | null;
  micOn?: boolean;
  camOn?: boolean;
  remoteMicOn?: boolean;
  remoteCamOn?: boolean;
  mediaCaption?: string;
  elapsedSeconds?: number;
  status?: CallViewStatus;
  joining?: boolean;
  cancelLabel?: string;
  onToggleMic?: () => void;
  onToggleCam?: () => void;
  onJoin?: () => void;
  onCancel?: () => void;
  onEnd?: () => void;
  onClose?: () => void;
};

function Video({ stream, muted, mirrored, className }: { stream?: MediaStream | null; muted?: boolean; mirrored?: boolean; className: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream ?? null;
  }, [stream]);
  return <video ref={ref} autoPlay playsInline muted={muted} className={`${className}${mirrored ? " mirrored" : ""}`} />;
}

export function CallView(props: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const isLive = props.mode === "active" || props.mode === "reconnecting";
  const showRemoteVideo = isLive && props.remoteCamOn !== false && props.remoteStream != null;
  const showLocalVideo = props.camOn !== false && props.localStream != null;
  const timer = formatDuration(props.elapsedSeconds ?? 0);

  const [isFullscreen, setIsFullscreen] = useState(false);
  useEffect(() => {
    const sync = () => setIsFullscreen(document.fullscreenElement === rootRef.current);
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);
  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void rootRef.current?.requestFullscreen();
  };
  // В полноэкранном режиме крестик сначала выходит из fullscreen, а не завершает звонок.
  const handleClose = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
      return;
    }
    props.onClose?.();
  };

  return (
    <div className="hub-call-view" ref={rootRef}>
      <header className="hub-call-head">
        <span className="hub-call-avatar small" style={{ background: props.peerAvatarColor ?? "#1677ff" }}>{props.peerInitials}</span>
        <div className="hub-call-head-info">
          <div className="hub-call-peer">{props.peerName}{props.channelBadge}</div>
          <span>{props.subtitle}</span>
        </div>
        {isLive && <span className={`hub-call-timer ${props.mode === "reconnecting" ? "warn" : ""}`}><i />{timer}</span>}
        {props.onClose && <button className="hub-call-close" onClick={handleClose} aria-label={isFullscreen ? t("call.exit_fullscreen") : t("call.close")}><CloseIcon /></button>}
      </header>

      <div className="hub-call-media">
        {/* Пока звонок активен, поток собеседника всегда смонтирован — иначе при
            выключенной камере (аудиозвонок) звук не воспроизводится. Когда камеры
            нет, видео перекрывается аватаром, но аудиодорожка играет. */}
        {isLive && props.remoteStream != null && <Video stream={props.remoteStream} className="hub-call-remote-video" />}

        {props.mode === "ringing" && (
          <CallAvatar name={props.peerName} initials={props.peerInitials} color={props.peerAvatarColor} caption={t("call.calling")} rings />
        )}

        {props.mode === "precall" && (
          showLocalVideo
            ? <Video stream={props.localStream} muted mirrored className="hub-call-preview-video" />
            : <CallAvatar name={t("call.you")} initials={t("call.you_initials")} color="#595959" caption={props.mediaCaption ?? t("call.camera_off")} />
        )}

        {isLive && !showRemoteVideo && (
          <CallAvatar name={props.peerName} initials={props.peerInitials} color={props.peerAvatarColor} caption={t("call.peer_camera_off")} />
        )}

        {isLive && (
          <>
            {props.mode === "reconnecting" && <div className="hub-call-reconnect"><SpinnerIcon />{t("call.reconnecting_inline")}</div>}
            <div className="hub-call-name-label">{props.remoteMicOn === false && <DeviceIcon kind="mic" on={false} />}<span>{props.peerName}</span></div>
            <div className="hub-call-pip">
              {showLocalVideo ? <Video stream={props.localStream} muted mirrored className="hub-call-local-video" /> : <span className="hub-call-avatar pip">{t("call.you_initials")}</span>}
              <b>{t("call.you")}</b>
            </div>
          </>
        )}

        {(props.mode === "connecting" || props.mode === "status") && props.status && <StatusView status={props.status} />}
      </div>

      {props.mode === "ringing" && props.onCancel && <RingingBar label={props.cancelLabel ?? t("call.cancel_call")} onClick={props.onCancel} />}
      {props.mode === "precall" && (
        <div className="hub-call-precall-bar">
          <div className="hub-call-device-row">
            <DeviceControl label={t("call.mic")} kind="mic" on={props.micOn !== false} onClick={props.onToggleMic} />
            <DeviceControl label={t("call.camera")} kind="cam" on={props.camOn !== false} onClick={props.onToggleCam} />
          </div>
          <div className="hub-call-join-row">
            <button className="secondary" onClick={props.onCancel}>{props.cancelLabel ?? t("call.cancel")}</button>
            <button className="primary" onClick={props.onJoin} disabled={props.joining}>{props.joining ? t("call.joining") : t("call.join")}</button>
          </div>
        </div>
      )}
      {isLive && (
        <div className="hub-call-active-bar">
          <DeviceButton kind="mic" on={props.micOn !== false} onClick={props.onToggleMic} />
          <DeviceButton kind="cam" on={props.camOn !== false} onClick={props.onToggleCam} />
          <button className="hub-call-round" onClick={toggleFullscreen} aria-label={isFullscreen ? t("call.exit_fullscreen") : t("call.enter_fullscreen")}><FullscreenIcon /></button>
          <button className="hub-call-end" onClick={props.onEnd} aria-label={t("call.end")}><PhoneIcon /></button>
        </div>
      )}
    </div>
  );
}

function CallAvatar({ name, initials, color, caption, rings }: { name: string; initials: string; color?: string; caption: string; rings?: boolean }) {
  return <div className="hub-call-avatar-stage"><div className={`hub-call-avatar-wrap${rings ? " rings" : ""}`}><i /><i /><span className="hub-call-avatar big" style={{ background: color ?? "#1677ff" }}>{initials}</span></div><div><strong>{name}</strong><span>{caption}</span></div></div>;
}

function StatusView({ status }: { status: CallViewStatus }) {
  return <div className="hub-call-status"><span className={`hub-call-status-icon ${status.tone}`}><StatusIcon name={status.icon} /></span><div><strong>{status.title}</strong><p>{status.caption}</p></div>{status.actions && <div className="hub-call-status-actions">{status.actions.map((action) => <button key={action.label} className={action.kind} onClick={action.onClick}>{action.label}</button>)}</div>}</div>;
}

function DeviceButton({ kind, on, onClick }: { kind: "mic" | "cam"; on: boolean; onClick?: () => void }) {
  return <button className={`hub-call-device${on ? "" : " off"}`} onClick={onClick} aria-label={kind === "mic" ? t("call.mic") : t("call.camera")}><DeviceIcon kind={kind} on={on} /></button>;
}

function DeviceControl({ label, kind, on, onClick }: { label: string; kind: "mic" | "cam"; on: boolean; onClick?: () => void }) {
  return <div className="hub-call-device-control"><DeviceButton kind={kind} on={on} onClick={onClick} /><span>{label}</span></div>;
}

function RingingBar({ label, onClick }: { label: string; onClick: () => void }) {
  return <div className="hub-call-ringing-bar"><button className="hub-call-end round" onClick={onClick} aria-label={label}><PhoneIcon /></button><span>{label}</span></div>;
}

function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
