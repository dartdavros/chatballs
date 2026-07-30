import { type AudioCallMode, type AudioCallStatus, type CallViewMode, type CallViewStatus, buildAudioStatus } from "@edevs/ui";

import type { CallInfo } from "../api";

const TERMINAL: Record<string, { icon: CallViewStatus["icon"]; tone: "neutral" | "error" | "warn"; title: string; caption: string }> = {
  DECLINED: { icon: "declined", tone: "neutral", title: "Звонок отклонён", caption: "Вы отклонили вызов. Продолжить общение можно в чате." },
  CANCELLED: { icon: "declined", tone: "neutral", title: "Звонок отменён", caption: "Сотрудник отменил приглашение. Продолжить общение можно в чате." },
  MISSED: { icon: "missed", tone: "warn", title: "Пропущенный звонок", caption: "Никто не ответил вовремя. Запросите новое приглашение в чате." },
  EXPIRED: { icon: "clock", tone: "warn", title: "Время ожидания истекло", caption: "Приглашение истекло. Запросите новое приглашение в чате." },
  ENDED: { icon: "declined", tone: "neutral", title: "Звонок завершён", caption: "Спасибо! Продолжить общение можно в чате." },
  FAILED: { icon: "alert", tone: "error", title: "Не удалось соединиться", caption: "Проверьте интернет-соединение и попробуйте снова по ссылке из чата." },
};

export const isTerminalCall = (status?: string) => Boolean(status && TERMINAL[status]);

export function resolveCallViewMode(state: { loading: boolean; invalid: boolean; call: CallInfo | null; started: boolean; connection: string; mediaIssue: string }): CallViewMode {
  if (state.loading || state.invalid || !state.call || isTerminalCall(state.call.status) || state.connection === "failed" || state.mediaIssue === "devices" || state.mediaIssue === "unsupported") return "status";
  if (!state.started) return "precall";
  if (state.connection === "reconnecting") return "reconnecting";
  if (state.connection === "connected" || state.call.status === "ACTIVE") return "active";
  return "connecting";
}

export function buildCallViewStatus(state: { loading: boolean; invalid: boolean; call: CallInfo | null; connection: string; mediaIssue: string; close: () => void; retry: () => void; prepare: () => void; join: () => void }): CallViewStatus | undefined {
  if (state.loading) return { icon: "spinner", tone: "neutral", title: "Проверяем приглашение", caption: "Секунду…" };
  if (state.invalid || !state.call) return { icon: "clock", tone: "warn", title: "Приглашение недействительно", caption: "Ссылка устарела или уже была использована. Запросите новое приглашение в чате." };
  if (state.mediaIssue === "unsupported") return { icon: "unsupported", tone: "error", title: "Видеозвонки не поддерживаются", caption: "Обновите браузер или откройте ссылку в Chrome, Safari или Edge." };
  if (state.mediaIssue === "devices") return { icon: "alert", tone: "error", title: "Нет доступа к камере и микрофону", caption: "Разрешите доступ к устройствам в настройках браузера и повторите.", actions: [{ label: "Повторить проверку", kind: "primary", onClick: state.prepare }, { label: "Без видео", kind: "secondary", onClick: state.join }] };
  if (state.connection === "failed") return { icon: "alert", tone: "error", title: "Не удалось соединиться", caption: "Проверьте интернет-соединение и попробуйте снова.", actions: [{ label: "Повторить", kind: "primary", onClick: state.retry }] };
  const terminal = TERMINAL[state.call.status];
  if (terminal) {
    const duration = state.call.status === "ENDED" && state.call.durationSeconds != null ? `Длительность ${formatDuration(state.call.durationSeconds)}. ` : "";
    return { ...terminal, caption: duration + terminal.caption, actions: [{ label: "Закрыть", kind: "secondary", onClick: state.close }] };
  }
  return { icon: "spinner", tone: "neutral", title: "Соединяем звонок", caption: "Устанавливаем защищённое соединение…" };
}

export function callViewSubtitle(mode: CallViewMode, status?: CallViewStatus) {
  if (mode === "precall") return "Проверьте камеру и микрофон";
  if (mode === "active") return "Активный звонок";
  if (mode === "reconnecting") return "Переподключение";
  return status?.title ?? "Соединение";
}

// --- Аудиозвонок (baseline «Аудиозвонок.dc.html»): incoming → active → терминал,
// без pre-call. Статус-центр — через общий buildAudioStatus из @edevs/ui. ---

export function resolveAudioCallViewMode(state: { loading: boolean; invalid: boolean; call: CallInfo | null; started: boolean; connection: string; mediaIssue: string }): AudioCallMode {
  if (state.loading || state.invalid || !state.call) return "status";
  if (state.mediaIssue === "devices" || state.mediaIssue === "unsupported") return "status";
  if (isTerminalCall(state.call.status) || state.connection === "failed") return "status";
  if (!state.started) return state.call.status === "RINGING" || state.call.status === "REQUESTED" ? "ringing" : "incoming";
  if (state.connection === "reconnecting") return "reconnecting";
  if (state.connection === "connected" || state.call.status === "ACTIVE") return "active";
  return "connecting";
}

export function buildAudioCallViewStatus(state: { loading: boolean; invalid: boolean; call: CallInfo | null; connection: string; mediaIssue: string; close: () => void }): AudioCallStatus | undefined {
  if (state.loading) return { icon: "clock", tone: "warn", title: "Проверяем приглашение", caption: "Секунду…", bar: "ended" };
  if (state.invalid || !state.call) return { icon: "clock", tone: "warn", title: "Приглашение недействительно", caption: "Ссылка устарела или уже была использована. Запросите новое приглашение в чате.", bar: "ended" };
  if (state.mediaIssue === "unsupported") return buildAudioStatus("unsupported", state.call.staffName || "Оператор") ?? undefined;
  if (state.mediaIssue === "devices") return buildAudioStatus("nodevice", state.call.staffName || "Оператор") ?? undefined;
  if (state.connection === "failed") return buildAudioStatus("FAILED", state.call.staffName || "Оператор") ?? undefined;
  const key = state.call.status === "ACCEPTED" || state.call.status === "CONNECTING" ? "connecting" : state.call.status;
  return buildAudioStatus(key, state.call.staffName || "Оператор", state.call.durationSeconds ?? undefined) ?? undefined;
}

export function audioCallStatusLabel(mode: AudioCallMode, status?: AudioCallStatus): string {
  if (status) return status.title;
  if (mode === "incoming") return "Входящий звонок";
  if (mode === "ringing") return "Соединение";
  if (mode === "active") return "Аудиозвонок";
  if (mode === "connecting") return "Соединение";
  if (mode === "reconnecting") return "Переподключение";
  return "Звонок завершён";
}

function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
