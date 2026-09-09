// Состояния аудиозвонка и сопутствующие данные (baseline «Аудиозвонок.dc.html»).
// Тексты/иконки/тоны вынесены отдельно, чтобы AudioCallView оставался
// composition-only и не смешивал разметку со справочником состояний.

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
  return duration != null && duration > 0 ? `${prefix}Длительность ${formatDuration(duration)}. ` : prefix;
}

// Справочник статусов-центров: процессы + ошибки + терминалы.
// `duration` подставляется только там, где разговор реально состоялся.
export function buildAudioStatus(status: string, peerName: string, duration?: number | null): AudioStatusEntry | null {
  const p = `${peerName} `;
  switch (status) {
    case "connecting":
    case "CONNECTING":
      return { icon: "spinner", tone: "neutral", title: "Соединяем", caption: "Устанавливаем защищённое соединение…", bar: "ended" };
    case "reconnecting":
      return { icon: "spinner", tone: "neutral", title: "Связь прервана", caption: "Восстанавливаем соединение…", bar: "reconnect" };
    case "DECLINED":
      return { icon: "declined", tone: "neutral", title: "Звонок отклонён", caption: `${p}отклонил(а) вызов.`, bar: "retrySingle" };
    case "MISSED":
      return { icon: "missed", tone: "warn", title: "Пропущенный звонок", caption: `${p}не ответил(а) на вызов.`, bar: "retrySingle" };
    case "EXPIRED":
      return { icon: "clock", tone: "warn", title: "Время ожидания истекло", caption: "Никто не ответил вовремя. Попробуйте позвонить снова.", bar: "retrySingle" };
    case "CANCELLED":
      return { icon: "declined", tone: "neutral", title: "Звонок отменён", caption: "Приглашение отменено.", bar: "ended" };
    case "FAILED":
      return { icon: "alert", tone: "error", title: "Не удалось соединиться", caption: `${dur("", duration)}Проверьте интернет-соединение и попробуйте снова.`, bar: "retryClose" };
    case "ENDED":
      return { icon: "clock", tone: "neutral", title: "Звонок завершён", caption: `${dur("", duration)}Разговор завершён.`, bar: "ended" };
    case "nodevice":
      return { icon: "nodevice", tone: "error", title: "Нет доступа к микрофону", caption: "Разрешите доступ к микрофону в настройках браузера и повторите.", bar: "retryCheck" };
    case "unsupported":
      return { icon: "unsupported", tone: "error", title: "Аудиозвонки не поддерживаются", caption: "Обновите браузер или откройте ссылку в Chrome, Safari или Edge.", bar: "retryCheck" };
    default:
      return null;
  }
}

export function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
