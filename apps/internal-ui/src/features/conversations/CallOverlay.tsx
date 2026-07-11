import { Modal } from "antd";

import { channelMeta } from "./data";
import type { ApiCall } from "./model";
import type { ConversationListItem } from "./types";
import "./call.css";

// Экран звонка оператора (SPEC-HUB-0013 §6, DG-07): ожидание ответа, отмена
// приглашения и терминальные состояния по baseline «Экран звонка.dc.html».
// Медиасостояния (pre-call, active) подключаются на этапе WebRTC-signaling.

type StatusView = {
  icon: "spinner" | "alert" | "declined" | "missed" | "clock";
  tone: "neutral" | "error" | "warn";
  title: string;
  caption: (name: string) => string;
  retry?: string;
};

const STATUS_VIEW: Partial<Record<ApiCall["status"], StatusView>> = {
  ACCEPTED: { icon: "spinner", tone: "neutral", title: "Соединяем звонок", caption: () => "Клиент принял приглашение. Устанавливаем защищённое соединение…" },
  CONNECTING: { icon: "spinner", tone: "neutral", title: "Соединяем звонок", caption: () => "Устанавливаем защищённое соединение…" },
  DECLINED: { icon: "declined", tone: "neutral", title: "Звонок отклонён", caption: (name) => `${name} отклонил(а) вызов.`, retry: "Позвонить снова" },
  MISSED: { icon: "missed", tone: "warn", title: "Пропущенный звонок", caption: (name) => `${name} не ответил(а) на вызов.`, retry: "Перезвонить" },
  EXPIRED: { icon: "clock", tone: "warn", title: "Время ожидания истекло", caption: () => "Никто не ответил вовремя. Попробуйте позвонить снова.", retry: "Позвонить снова" },
  CANCELLED: { icon: "declined", tone: "neutral", title: "Звонок отменён", caption: () => "Приглашение отменено." },
  FAILED: { icon: "alert", tone: "error", title: "Не удалось соединиться", caption: () => "Проверьте интернет-соединение и попробуйте снова.", retry: "Повторить" },
  ENDED: { icon: "declined", tone: "neutral", title: "Звонок завершён", caption: () => "Разговор завершён." },
};

const SUBTITLES: Partial<Record<ApiCall["status"], string>> = {
  REQUESTED: "Отправляем приглашение",
  RINGING: "Ожидание ответа",
  ACCEPTED: "Соединение",
  CONNECTING: "Соединение",
};

export function CallOverlay({ open, dialog, call, errorText, onCancel, onRetry, onClose }: {
  open: boolean;
  dialog: ConversationListItem | null;
  call: ApiCall | null;
  errorText: string;
  onCancel: () => void;
  onRetry: () => void;
  onClose: () => void;
}) {
  if (!dialog) return null;
  const channel = channelMeta[dialog.channel];
  const isWaiting = call != null && (call.status === "REQUESTED" || call.status === "RINGING");
  const status = errorText
    ? { icon: "alert" as const, tone: "error" as const, title: "Не удалось запросить звонок", caption: () => errorText, retry: undefined }
    : call
      ? STATUS_VIEW[call.status]
      : undefined;
  const subtitle = errorText ? "Ошибка" : (call && (SUBTITLES[call.status] ?? status?.title)) || "";
  const caption = call?.status === "ENDED" && call.durationSeconds != null
    ? `Длительность ${fmtDuration(call.durationSeconds)}.`
    : status?.caption(dialog.name);
  // Действий нет только у промежуточного «Соединяем звонок» — его закроет
  // grace period сервера или переход в активный звонок.
  const connectingPhase = !errorText && (call?.status === "ACCEPTED" || call?.status === "CONNECTING");
  const showActions = status != null && !connectingPhase;

  return (
    <Modal open={open} onCancel={onClose} footer={null} closable={false} width={428} className="call-modal" destroyOnHidden>
      <div className="call-head">
        <span className="call-head-avatar" style={{ background: dialog.avatarBg }}>{dialog.initials}</span>
        <div className="call-head-info">
          <div className="call-head-name">
            {dialog.name}
            <em style={{ background: channel.bg, color: channel.color }}>{channel.label}</em>
          </div>
          <span className="call-head-subtitle">{subtitle}</span>
        </div>
        <button className="call-head-close" onClick={onClose} aria-label="Закрыть">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
        </button>
      </div>

      <div className="call-media">
        {isWaiting && !status && (
          <div className="call-media-center">
            <div className="call-rings">
              <i /><i />
              <span className="call-big-avatar" style={{ background: dialog.avatarBg }}>{dialog.initials}</span>
            </div>
            <div className="call-media-name">
              <strong>{dialog.name}</strong>
              <span>Вызываем…</span>
            </div>
          </div>
        )}
        {status && (
          <div className="call-status">
            <span className={`call-status-icon ${status.tone}`}><StatusIcon name={status.icon} /></span>
            <div>
              <div className="call-status-title">{status.title}</div>
              <div className="call-status-caption">{caption}</div>
            </div>
            {showActions && (
              <div className="call-status-actions">
                {status.retry && <button className="primary" onClick={onRetry}>{status.retry}</button>}
                <button className="secondary" onClick={onClose}>Закрыть</button>
              </div>
            )}
          </div>
        )}
      </div>

      {isWaiting && (
        <div className="call-bar-ringing">
          <button className="call-hangup" onClick={onCancel} aria-label="Отменить вызов">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" style={{ transform: "rotate(135deg)" }}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>
          </button>
          <span>Отменить</span>
        </div>
      )}
    </Modal>
  );
}

function fmtDuration(seconds: number): string {
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function StatusIcon({ name }: { name: "spinner" | "alert" | "declined" | "missed" | "clock" }) {
  const common = { viewBox: "0 0 24 24", width: 26, height: 26, fill: "none", stroke: "currentColor", strokeWidth: 1.9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (name) {
    case "spinner":
      return <svg {...common} strokeWidth={2} style={{ animation: "callSpin .9s linear infinite" }}><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>;
    case "alert":
      return <svg {...common}><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>;
    case "declined":
      return <svg {...common}><path transform="rotate(135 12 12)" d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>;
    case "missed":
      return <svg {...common}><path d="M23 7l-8 8-4-4-9 9" /><polyline points="17 7 23 7 23 13" /></svg>;
    case "clock":
      return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
  }
}
