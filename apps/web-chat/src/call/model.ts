import { type AudioBarKind, type AudioCallMode, type AudioCallStatus, type CallViewMode, type CallViewStatus, buildAudioStatus, isTerminalCallStatus } from "@chatballs/ui";

import type { CallInfo } from "../api";
import { t } from "../i18n";

// Функция, а не константа: текст зависит от языка, а язык виджета приходит с
// настройками — то есть после того, как модуль уже импортирован.
function terminalStatuses(): Record<string, { icon: CallViewStatus["icon"]; tone: "neutral" | "error" | "warn"; title: string; caption: string }> {
  return {
    DECLINED: { icon: "declined", tone: "neutral", title: t("call.declined"), caption: t("call.declined_by_you") },
    CANCELLED: { icon: "declined", tone: "neutral", title: t("call.cancelled"), caption: t("call.cancelled_by_staff") },
    MISSED: { icon: "missed", tone: "warn", title: t("call.missed"), caption: t("call.nobody_answered_ask_again") },
    EXPIRED: { icon: "clock", tone: "warn", title: t("call.wait_timed_out"), caption: t("call.expired_ask_again") },
    ENDED: { icon: "declined", tone: "neutral", title: t("call.ended"), caption: t("call.thanks_continue_in_chat") },
    FAILED: { icon: "alert", tone: "error", title: t("call.could_not_connect"), caption: t("call.check_connection_link") },
  };
}

export const isTerminalCall = isTerminalCallStatus;

export function resolveCallViewMode(state: { loading: boolean; invalid: boolean; call: CallInfo | null; started: boolean; connection: string; mediaIssue: string; errorText?: string }): CallViewMode {
  if (state.loading || state.invalid || state.errorText || !state.call || isTerminalCall(state.call.status) || state.connection === "failed" || state.mediaIssue === "devices" || state.mediaIssue === "unsupported") return "status";
  if (!state.started) return "precall";
  if (state.connection === "reconnecting") return "reconnecting";
  if (state.connection === "connected" || state.call.status === "ACTIVE") return "active";
  return "connecting";
}

export function buildCallViewStatus(state: { loading: boolean; invalid: boolean; call: CallInfo | null; connection: string; mediaIssue: string; errorText?: string; close: () => void; retry: () => void; prepare: () => void; join: () => void }): CallViewStatus | undefined {
  if (state.loading) return { icon: "spinner", tone: "neutral", title: t("call.checking_invite"), caption: t("call.one_moment") };
  if (state.invalid || !state.call) return { icon: "clock", tone: "warn", title: t("call.invite_invalid"), caption: t("call.invite_stale") };
  if (state.errorText) return { icon: "alert", tone: "error", title: t("call.could_not_act"), caption: state.errorText, actions: [{ label: t("call.close"), kind: "secondary", onClick: state.close }] };
  if (state.mediaIssue === "unsupported") return { icon: "unsupported", tone: "error", title: t("call.video_not_supported"), caption: t("call.update_browser") };
  if (state.mediaIssue === "devices") return { icon: "alert", tone: "error", title: t("call.no_camera_mic_access"), caption: t("call.allow_devices"), actions: [{ label: t("call.retry_check"), kind: "primary", onClick: state.prepare }, { label: t("call.without_video"), kind: "secondary", onClick: state.join }] };
  if (state.connection === "failed") return { icon: "alert", tone: "error", title: t("call.could_not_connect"), caption: t("call.check_connection"), actions: [{ label: t("call.retry"), kind: "primary", onClick: state.retry }] };
  const terminal = terminalStatuses()[state.call.status];
  if (terminal) {
    const duration = state.call.status === "ENDED" && state.call.durationSeconds != null ? `${t("call.duration", { duration: formatDuration(state.call.durationSeconds) })} ` : "";
    return { ...terminal, caption: duration + terminal.caption, actions: [{ label: t("call.close"), kind: "secondary", onClick: state.close }] };
  }
  return { icon: "spinner", tone: "neutral", title: t("call.connecting"), caption: t("call.establishing") };
}

export function callViewSubtitle(mode: CallViewMode, status?: CallViewStatus) {
  if (mode === "precall") return t("call.check_camera_mic");
  if (mode === "active") return t("call.active");
  if (mode === "reconnecting") return t("call.reconnecting");
  return status?.title ?? t("call.connection");
}

// --- Аудиозвонок (baseline «Аудиозвонок.dc.html»): incoming → active → терминал,
// без pre-call. Статус-центр — через общий buildAudioStatus из @chatballs/ui. ---

export function resolveAudioCallViewMode(state: { loading: boolean; invalid: boolean; call: CallInfo | null; started: boolean; connection: string; mediaIssue: string; errorText?: string }): AudioCallMode {
  if (state.loading || state.invalid || state.errorText || !state.call) return "status";
  if (state.mediaIssue === "devices" || state.mediaIssue === "unsupported") return "status";
  if (isTerminalCall(state.call.status) || state.connection === "failed") return "status";
  // Приглашение для клиента — входящий звонок: он решает принять или отклонить
  // (звонок всегда инициирует сотрудник, поэтому «исходящего» для клиента нет).
  // REQUESTED/RINGING до старта → incoming (парные Принять/Отклонить).
  if (!state.started) return "incoming";
  if (state.connection === "reconnecting") return "reconnecting";
  if (state.connection === "connected" || state.call.status === "ACTIVE") return "active";
  return "connecting";
}

// Клиент не инициирует звонки (см. resolveAudioCallViewMode), поэтому «Позвонить
// снова» ему показывать нечем: обработчика нет, и кнопка выходила мёртвой — а на
// DECLINED/MISSED/EXPIRED она была единственной, и с экрана было не уйти.
const clientBar = (bar: AudioBarKind): AudioBarKind => (bar === "retrySingle" || bar === "ended" ? "close" : bar);

function clientStatus(status: AudioCallStatus | null): AudioCallStatus | undefined {
  return status ? { ...status, bar: clientBar(status.bar) } : undefined;
}

export function buildAudioCallViewStatus(state: { loading: boolean; invalid: boolean; call: CallInfo | null; connection: string; mediaIssue: string; errorText?: string; close: () => void }): AudioCallStatus | undefined {
  if (state.loading) return { icon: "clock", tone: "warn", title: t("call.checking_invite"), caption: t("call.one_moment"), bar: "close" };
  if (state.invalid || !state.call) return { icon: "clock", tone: "warn", title: t("call.invite_invalid"), caption: t("call.invite_stale"), bar: "close" };
  if (state.errorText) return { icon: "alert", tone: "error", title: t("call.could_not_act"), caption: state.errorText, bar: "retryClose" };
  if (state.mediaIssue === "unsupported") return clientStatus(buildAudioStatus("unsupported", state.call.staffName || t("call.operator")));
  if (state.mediaIssue === "devices") return clientStatus(buildAudioStatus("nodevice", state.call.staffName || t("call.operator")));
  if (state.connection === "failed") return clientStatus(buildAudioStatus("FAILED", state.call.staffName || t("call.operator")));
  const key = state.call.status === "ACCEPTED" || state.call.status === "CONNECTING" ? "connecting" : state.call.status;
  return clientStatus(buildAudioStatus(key, state.call.staffName || t("call.operator"), state.call.durationSeconds ?? undefined));
}

export function audioCallStatusLabel(mode: AudioCallMode, status?: AudioCallStatus): string {
  if (status) return status.title;
  if (mode === "incoming") return t("call.incoming");
  if (mode === "ringing") return t("call.connection");
  if (mode === "active") return t("call.audio_call");
  if (mode === "connecting") return t("call.connection");
  if (mode === "reconnecting") return t("call.reconnecting");
  return t("call.ended");
}

function formatDuration(seconds: number) {
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
