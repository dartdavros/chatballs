// Состояния аудиозвонка и сопутствующие данные (baseline «Аудиозвонок.dc.html»).
// Тексты/иконки/тоны вынесены отдельно, чтобы AudioCallView оставался
// composition-only и не смешивал разметку со справочником состояний.

import { t } from "../i18n";
import type { AudioStatusIconName } from "./AudioCallIcons";

export type AudioCallMode = "incoming" | "ringing" | "connecting" | "active" | "reconnecting" | "status";

export type AudioCallActionKind = "close" | "callAgain" | "retry" | "retryCheck" | "end";

export type AudioCallAction = { label: string; kind: AudioCallActionKind };

export type AudioCallStatus = {
  icon: AudioStatusIconName;
  tone: "neutral" | "warn" | "error";
  title: string;
  caption: string;
  bar: AudioBarKind;
};

// Какой нижний бар рисовать для текущего состояния (вне active/incoming/ringing/connecting).
// "close" — только «Закрыть»: сторона, которая не может инициировать звонок (клиент).
export type AudioBarKind = "ended" | "close" | "retrySingle" | "retryClose" | "reconnect" | "retryCheck";

export type AudioStatusEntry = AudioCallStatus;

// Терминальные состояния, приходящие из домена звонков (TERMINAL_CALL_STATUSES).
// Единственный источник правды для фронтенда: и аудио-, и видеозвонок, и оператор,
// и RTC-сессия сверяются с этим набором — раньше он был скопирован в четыре места.
export const TERMINAL_CALL_STATUSES = new Set([
  "DECLINED",
  "CANCELLED",
  "MISSED",
  "ENDED",
  "FAILED",
  "EXPIRED",
]);

export const isTerminalCallStatus = (status?: string) => Boolean(status && TERMINAL_CALL_STATUSES.has(status));

function dur(prefix: string, duration?: number | null) {
  return duration != null && duration > 0 ? `${prefix}${t("call.duration", { duration: formatDuration(duration) })} ` : prefix;
}

// Справочник статусов-центров: процессы + ошибки + терминалы.
// `duration` подставляется только там, где разговор реально состоялся.
export function buildAudioStatus(status: string, peerName: string, duration?: number | null): AudioStatusEntry | null {
  switch (status) {
    case "connecting":
    case "CONNECTING":
      return { icon: "spinner", tone: "neutral", title: t("call.connecting"), caption: t("call.establishing"), bar: "ended" };
    case "reconnecting":
      return { icon: "spinner", tone: "neutral", title: t("call.reconnecting_title"), caption: t("call.reconnecting_caption"), bar: "reconnect" };
    case "DECLINED":
      return { icon: "declined", tone: "neutral", title: t("call.call_declined"), caption: t("call.declined_by", { name: peerName }), bar: "retrySingle" };
    case "MISSED":
      return { icon: "missed", tone: "warn", title: t("call.missed"), caption: t("call.unanswered_by", { name: peerName }), bar: "retrySingle" };
    case "EXPIRED":
      return { icon: "clock", tone: "warn", title: t("call.wait_timed_out"), caption: t("call.nobody_answered"), bar: "retrySingle" };
    case "CANCELLED":
      return { icon: "declined", tone: "neutral", title: t("call.call_cancelled"), caption: t("call.invitation_cancelled"), bar: "ended" };
    case "FAILED":
      return { icon: "alert", tone: "error", title: t("call.unable_to_connect"), caption: `${dur("", duration)}${t("call.check_connection")}`, bar: "retryClose" };
    case "ENDED":
      return { icon: "clock", tone: "neutral", title: t("call.call_ended"), caption: `${dur("", duration)}${t("call.conversation_ended")}`, bar: "ended" };
    case "nodevice":
      return { icon: "nodevice", tone: "error", title: t("call.no_mic_access"), caption: t("call.allow_mic"), bar: "retryCheck" };
    case "unsupported":
      return { icon: "unsupported", tone: "error", title: t("call.audio_not_supported"), caption: t("call.link_unsupported_browser"), bar: "retryCheck" };
    default:
      return null;
  }
}

export function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
