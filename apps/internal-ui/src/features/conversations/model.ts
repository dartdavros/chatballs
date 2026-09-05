import { api, apiUpload } from "../../api/client";
import type { ChannelKey, ConversationListItem, ControlMode, DialogMode } from "./types";

// kind: "" — текст, "contact_request" — запрос контакта, "contact" — клиент поделился номером.
export type ApiMessage = {
  id: number;
  author: "CONTACT" | "AI" | "OPERATOR" | "SYSTEM";
  authorUserId?: number | null;
  authorName?: string;
  kind?: string;
  text: string;
  contentHtml?: string;
  createdAt: string;
  // Голосовое (kind="voice", дизайн-базлайн v2 кадр H).
  audioUrl?: string | null;
  durationSeconds?: number;
  transcript?: string;
  transcriptStatus?: "NONE" | "READY" | "FAILED";
};

export type HistoryItem = {
  id: number;
  channelName: string;
  provider: "EMAIL" | "MAX" | "TELEGRAM" | "WEB" | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  createdAt: string;
  lastActivityAt: string;
  preview: string;
};

// Краткая карточка support-снапшота в conversation_payload (list-режим).
export type SupportIdentitySnapshotRef = {
  id: number;
  subjectKey: string;
  displayName: string;
  displayEmail: string;
  contractCode: string;
  // Расширяется в detail-режиме (operatorContextJson для правой панели оператора).
  operatorContextJson?: { operator_cards: OperatorCard[] };
  accountKey?: string | null;
};

export type OperatorCardField = {
  label: string;
  value: unknown;
  type: string; // text|email|phone|url|code|badge|datetime|boolean|number; unknown→text
  visibility?: string;
};

export type OperatorCard = {
  title: string;
  fields: OperatorCardField[];
};

export type ConversationPriority = "HIGH" | "MEDIUM" | "LOW" | "NONE";

export type ConversationLabelRef = { id: number; name: string; color: string };

export type ConversationCounters = {
  all: number;
  waiting: number;
  mine: number;
  ungrouped: number;
  groups: Array<{ id: number; name: string; count: number }>;
  agents: Array<{ id: number; name: string; count: number }>;
};

export type ReplyTemplateRef = { id: number; title: string; text: string; updatedAt: string };

export type ApiConversation = {
  id: number;
  channel: { code: string; name: string; product: { code: string; name: string } | null };
  connection: { id: number; provider: "EMAIL" | "MAX" | "TELEGRAM" | "WEB"; name: string } | null;
  // Источник identity: sales Contact (лид) ИЛИ verified SupportIdentitySnapshot.
  // ADR-HUB-0022: ровно один заполнен.
  // phone появляется после явного шаринга контакта; username (@логин TG/MAX) — только в detail-режиме.
  contact: { id: number; name: string; email?: string; phone?: string; username?: string; avatarUrl?: string } | null;
  supportIdentitySnapshot: SupportIdentitySnapshotRef | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  controlMode: "AI" | "HUMAN" | "PAUSED";
  expectedResponder: string;
  assignedOperatorId: number | null;
  assignedOperator: { id: number; name: string } | null;
  isAssignedToViewer: boolean;
  group: { id: number; name: string } | null;
  // Дизайн-базлайн v2: приоритет, метки, заметка, архив.
  priority: ConversationPriority;
  labels: ConversationLabelRef[];
  note: string;
  archivedAt: string | null;
  lastActivityAt: string;
  createdAt: string;
  lastMessage: ApiMessage | null;
  pendingCount?: number;
  messages?: ApiMessage[];
  history?: HistoryItem[];
};

const AVATAR_PALETTE = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4413b", "#6b5be0"];
// Цвет агента (решение 6a: Консультант — фиолетовый, Поддержка сайта — бирюзовый)
// и цвет точки группы — стабильно из идентификатора.
const AGENT_PALETTE = ["var(--ai)", "#0f9b8e", "#6d5dfc", "#e8590c", "#d4860b"];
const GROUP_PALETTE = ["var(--primary)", "#2aa876", "#e8590c", "#6d5dfc", "#d4860b"];

function hashCode(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  return hash;
}

export function agentColorOf(code: string): string {
  return AGENT_PALETTE[hashCode(code) % AGENT_PALETTE.length];
}

export function groupColorOf(groupId: number): string {
  return GROUP_PALETTE[groupId % GROUP_PALETTE.length];
}

// Время в строке списка: сегодня — часы, вчера — «вчера», дальше — дата.
export function listTime(iso: string, now = new Date()): string {
  const date = new Date(iso);
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return "вчера";
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }).replace(".", "");
}

// Таймер ожидания оператора: «6 мин», «1 ч 50 мин» — без слова «ждёт» (решение 4).
export function waitLabelOf(sinceIso: string, now = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(sinceIso).getTime()) / 60000));
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)} д`;
  const rest = minutes % 60;
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
}
const PROVIDER_CHANNEL: Record<string, ChannelKey> = {
  EMAIL: "EMAIL",
  MAX: "MAX",
  TELEGRAM: "TG",
  WEB: "WEB",
};

export function controlModeOf(conversation: ApiConversation): ControlMode {
  if (conversation.lifecycle !== "OPEN") return "closed";
  if (conversation.controlMode === "HUMAN") {
    return conversation.isAssignedToViewer ? "human" : "assigned";
  }
  if (conversation.controlMode === "AI") return "ai";
  return "waiting";
}

function dialogMode(conversation: ApiConversation): DialogMode {
  if (conversation.lifecycle === "CLOSED") return "closed";
  if (conversation.controlMode === "HUMAN") return "operator";
  if (conversation.controlMode === "AI") return "ai";
  return "wait";
}

function formatPreviewDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "Г";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}

// Имя клиента: sales contact ИЛИ snapshot displayName, fallback на subject_key.
export function conversationName(conversation: ApiConversation): string {
  if (conversation.contact) return conversation.contact.name || `Гость ${conversation.contact.id}`;
  const snapshot = conversation.supportIdentitySnapshot;
  if (snapshot) return snapshot.displayName || `client:${snapshot.subjectKey.slice(0, 8)}`;
  return "Гость";
}

export function toConversationListItem(conversation: ApiConversation): ConversationListItem {
  const name = conversationName(conversation);
  // avatarBg: стабильно из id источника identity.
  const seed = conversation.contact?.id ?? conversation.supportIdentitySnapshot?.id ?? conversation.id;
  return {
    id: conversation.id,
    name,
    initials: initialsOf(name),
    avatarBg: AVATAR_PALETTE[seed % AVATAR_PALETTE.length],
    avatarUrl: conversation.contact?.avatarUrl || undefined,
    product: conversation.channel.name,
    channel: PROVIDER_CHANNEL[conversation.connection?.provider ?? "WEB"] ?? "WEB",
    email: conversation.contact?.email ?? "",
    mode: dialogMode(conversation),
    preview:
      conversation.lastMessage?.kind === "voice"
        ? `Голосовое сообщение · ${formatPreviewDuration(conversation.lastMessage.durationSeconds ?? 0)}`
        : conversation.lastMessage?.text.replace(/\s+/g, " ").slice(0, 80) ?? "—",
    time: listTime(conversation.lastActivityAt),
    unread: conversation.pendingCount ?? 0,
    isMine: conversation.isAssignedToViewer,
    priority: conversation.priority ?? "NONE",
    labels: conversation.labels ?? [],
    agentName: conversation.channel.name,
    agentColor: agentColorOf(conversation.channel.code),
    groupName: conversation.group?.name ?? null,
    groupColor: conversation.group ? groupColorOf(conversation.group.id) : "var(--n-5)",
    waitLabel:
      conversation.lifecycle === "OPEN" && conversation.controlMode === "PAUSED"
        ? waitLabelOf(conversation.lastActivityAt)
        : null,
    lastIsOurs: conversation.lastMessage?.author === "OPERATOR" || conversation.lastMessage?.author === "AI",
  };
}

// Видимость inbox решает backend (ADR-HUB-0043): группы сотрудника + без группы
// + назначенные ему; владелец и админ видят всё. Фильтры — серверные.
export type ConversationListFilters = Partial<{
  group: string; // id | "none"
  agent: number; // id канала-агента
  assigned: "me";
  waiting: boolean;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  archived: boolean;
  q: string;
}>;

export const fetchConversations = (filters: ConversationListFilters = {}) => {
  const params = new URLSearchParams();
  if (filters.group) params.set("group", filters.group);
  if (filters.agent) params.set("agent", String(filters.agent));
  if (filters.assigned) params.set("assigned", filters.assigned);
  if (filters.waiting) params.set("waiting", "1");
  if (filters.lifecycle) params.set("lifecycle", filters.lifecycle);
  if (filters.archived) params.set("archived", "1");
  if (filters.q) params.set("q", filters.q);
  const suffix = params.size ? `?${params.toString()}` : "";
  return api<{ items: ApiConversation[] }>(`/api/v1/conversations/${suffix}`).then((r) => r.items);
};
export const fetchConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/`).then((r) => r.conversation);
export const claimConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/claim/`, { method: "POST" }).then((r) => r.conversation);
export const releaseConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/release/`, { method: "POST" }).then((r) => r.conversation);
export const sendOperatorMessage = (id: number, text: string) => api(`/api/v1/conversations/${id}/messages/`, { method: "POST", body: JSON.stringify({ text }) });
export const returnToQueue = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/return-queue/`, { method: "POST" }).then((r) => r.conversation);
// Запрос контакта: в TG/MAX клиент видит кнопку «Поделиться контактом», в веб-чате — форму телефона.
export const requestContact = (id: number) => api(`/api/v1/conversations/${id}/request-contact/`, { method: "POST" });
export const closeConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/close/`, { method: "POST" }).then((r) => r.conversation);
export const markConversationAsSpam = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/spam/`, { method: "POST" }).then((r) => r.conversation);
// Бейдж ожидающих диалогов. ConversationStatsView сейчас sales-only (SPEC §12:
// support-метрики — отдельный endpoint); department-параметр backend не использует.
export const fetchWaitingCount = () => api<{ waiting: number }>("/api/v1/conversations/stats/").then((r) => r.waiting);

// --- Дизайн-базлайн v2: карточка «Диалог», метки, шаблоны, счётчики ---

const conversationAction = (id: number, suffix: string, body: object) =>
  api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/${suffix}/`, {
    method: "POST",
    body: JSON.stringify(body),
  }).then((r) => r.conversation);

export const setConversationPriority = (id: number, priority: ConversationPriority) =>
  conversationAction(id, "priority", { priority });
export const setConversationNote = (id: number, note: string) =>
  conversationAction(id, "note", { note });
export const setConversationLabels = (id: number, labelIds: number[]) =>
  conversationAction(id, "labels", { labelIds });
export const setConversationArchived = (id: number, archived: boolean) =>
  conversationAction(id, "archive", { archived });
export const setConversationGroup = (id: number, groupId: number | null) =>
  conversationAction(id, "group", { groupId });
export const setConversationAssignee = (id: number, userId: number | null) =>
  conversationAction(id, "assignee", { userId });

export const fetchConversationCounters = () =>
  api<ConversationCounters>("/api/v1/conversations/counters/");
export const fetchConversationLabels = () =>
  api<{ items: ConversationLabelRef[] }>("/api/v1/conversations/labels/").then((r) => r.items);
export const createConversationLabel = (name: string, color = "") =>
  api<{ label: ConversationLabelRef }>("/api/v1/conversations/labels/", {
    method: "POST",
    body: JSON.stringify({ name, color }),
  }).then((r) => r.label);
export const fetchReplyTemplates = () =>
  api<{ items: ReplyTemplateRef[] }>("/api/v1/conversations/templates/").then((r) => r.items);

export const transcribeMessage = (messageId: number) =>
  api<{ message: ApiMessage }>(`/api/v1/conversations/messages/${messageId}/transcribe/`, { method: "POST" }).then((r) => r.message);

export const sendVoiceMessage = (conversationId: number, audio: Blob, durationSeconds: number) => {
  const form = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : audio.type.includes("webm") ? "webm" : "bin";
  form.append("audio", audio, `voice.${extension}`);
  form.append("duration", String(Math.round(durationSeconds)));
  return apiUpload<{ message: ApiMessage }>(`/api/v1/conversations/${conversationId}/voice/`, form).then((r) => r.message);
};

// --- Онлайн-звонки (SPEC-HUB-0013): запрос из диалога, ожидание, отмена ---

export type CallKind = "AUDIO" | "VIDEO";

export type ApiCall = {
  id: string;
  conversationId: number;
  status: "REQUESTED" | "RINGING" | "ACCEPTED" | "CONNECTING" | "ACTIVE" | "DECLINED" | "CANCELLED" | "MISSED" | "ENDED" | "FAILED" | "EXPIRED";
  kind: CallKind;
  requestedAt: string;
  acceptedAt: string | null;
  connectedAt: string | null;
  endedAt: string | null;
  endedBy: string | null;
  failureCode: string | null;
  durationSeconds: number | null;
};

export type CallAccess = { accessToken: string; iceServers: RTCIceServer[] };
export type CreatedCall = { call: ApiCall; access: CallAccess };

// Запрос звонка: при режиме AI backend атомарно выполняет takeover (§6).
export const requestCall = (conversationId: number, kind: CallKind = "AUDIO") =>
  api<{ call: ApiCall; staffAccessToken: string; iceServers: RTCIceServer[] }>(`/api/v1/calls/conversations/${conversationId}/`, { method: "POST", body: JSON.stringify({ kind }) })
    .then((r): CreatedCall => ({ call: r.call, access: { accessToken: r.staffAccessToken, iceServers: r.iceServers } }));
export const fetchActiveCall = (conversationId: number) =>
  api<{ call: ApiCall | null }>(`/api/v1/calls/conversations/${conversationId}/active/`).then((r) => r.call);
export const fetchCall = (callId: string) => api<{ call: ApiCall }>(`/api/v1/calls/${callId}/`).then((r) => r.call);
export const cancelCall = (callId: string) => api<{ call: ApiCall }>(`/api/v1/calls/${callId}/cancel/`, { method: "POST" }).then((r) => r.call);
export const fetchStaffCallAccess = (callId: string) =>
  api<{ accessToken: string; iceServers: RTCIceServer[] }>(`/api/v1/calls/${callId}/access-token/`, { method: "POST" });
export const endCallByAccess = (accessToken: string) =>
  api<{ call: ApiCall }>("/api/v1/calls/access/end/", { method: "POST", headers: { Authorization: `Bearer ${accessToken}` } }).then((r) => r.call);
