import { api, apiUpload } from "../../api/client";
import type { ChannelKey, ConversationListItem, ControlMode, DialogMode, ListSort } from "./types";
import { t } from "../../i18n";

// kind: "" — текст, "contact_request" — запрос контакта, "contact" — клиент поделился номером.
export type ApiMessage = {
  id: number;
  author: "CONTACT" | "AI" | "OPERATOR" | "SYSTEM";
  authorUserId?: number | null;
  authorName?: string;
  authorAvatarUrl?: string | null;
  kind?: string;
  text: string;
  // Код системного события: строку сервер уже собрал на языке читателя, код
  // остаётся интерфейсу для тона строки.
  systemEvent?: string;
  contentHtml?: string;
  createdAt: string;
  // Голосовое (kind="voice", дизайн-базлайн v2 кадр H).
  audioUrl?: string | null;
  durationSeconds?: number;
  transcript?: string;
  transcriptStatus?: "NONE" | "READY" | "FAILED";
  // Файл или фото (kind="file"): text — подпись.
  attachmentUrl?: string | null;
  attachmentName?: string;
  attachmentContentType?: string;
  attachmentSize?: number;
};

export const isImageAttachment = (message: Pick<ApiMessage, "attachmentContentType">) =>
  /^image\/(jpeg|png|gif|webp)$/.test(message.attachmentContentType ?? "");

export type HistoryItem = {
  id: number;
  channelName: string;
  provider: "EMAIL" | "MAX" | "TELEGRAM" | "WEB" | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  createdAt: string;
  lastActivityAt: string;
  topic?: string;
  handledBy?: string | null;
  preview: string;
};

export type ConversationPriority = "HIGH" | "MEDIUM" | "LOW" | "NONE";

export type ConversationLabelRef = { id: number; name: string; color: string };

export type ConversationCounters = {
  all: number;
  waiting: number;
  mine: number;
  ungrouped: number;
  groups: Array<{ id: number; name: string; color?: string; count: number }>;
  agents: Array<{ id: number; code: string; name: string; count: number }>;
  assignees: Array<{ id: number; name: string; count: number; avatarUrl?: string | null }>;
};

export type ReplyTemplateRef = { id: number; title: string; text: string; updatedAt: string };

export type ApiConversation = {
  id: number;
  channel: { id: number; code: string; name: string };
  // voiceMessages/audioCalls/videoCalls — что разрешено в точке входа («Настройки → Голосовые и звонки»).
  connection: { id: number; provider: "EMAIL" | "MAX" | "TELEGRAM" | "WEB"; name: string; voiceMessages?: boolean; audioCalls?: boolean; videoCalls?: boolean } | null;
  // Контакт — единственный источник identity диалога.
  // phone появляется после явного шаринга контакта; username (@логин TG/MAX) — только в detail-режиме.
  contact: { id: number; name: string; email?: string; phone?: string; username?: string; avatarUrl?: string; description?: string; company?: string; city?: string } | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  controlMode: "AI" | "HUMAN" | "PAUSED";
  expectedResponder: string;
  assignedOperatorId: number | null;
  assignedOperator: { id: number; name: string; avatarUrl?: string | null } | null;
  isAssignedToViewer: boolean;
  group: { id: number; name: string; color?: string } | null;
  // Дизайн-базлайн v2: приоритет, метки, заметка, архив.
  priority: ConversationPriority;
  labels: ConversationLabelRef[];
  note: string;
  archivedAt: string | null;
  lastActivityAt: string;
  createdAt: string;
  lastMessage: ApiMessage | null;
  pendingCount?: number;
  // Сообщений в карточке нет: история — отдельная лента с окном (fetchMessages).
  history?: HistoryItem[];
  // Запрос контакта мог уйти вне загруженного окна истории — факт считает сервер.
  contactRequested?: boolean;
};

// Живые ленты (инбокс, история диалога) приходят окном: записи, признак
// продолжения и курсор на следующее окно.
export type WindowPage<T> = { items: T[]; hasMore: boolean; cursor: number | null };

const AVATAR_PALETTE = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4413b", "#6b5be0"];
// Цвет агента и цвет точки группы — стабильно из идентификатора. Палитра идёт
// по порядку создания агентов, как в дизайн-базлайне (решение 6a): первый
// агент «Консультант» — фиолетовый, второй «Поддержка сайта» — бирюзовый,
// четвёртый «Приёмная» — оранжевый. Хеш кода здесь не годился: он давал
// и другие цвета, и совпадения у разных агентов.
const AGENT_PALETTE = ["var(--ai)", "#0f9b8e", "#6d5dfc", "#e8590c", "#d4860b"];
const GROUP_PALETTE = ["var(--primary)", "#2aa876", "#e8590c", "#6d5dfc", "#d4860b"];

export function agentColorOf(agentId: number): string {
  return AGENT_PALETTE[(agentId - 1) % AGENT_PALETTE.length];
}

// Цвет группы — заданный в настройках (дизайн-базлайн v2), иначе палитра по id.
export function groupColorOf(groupId: number, color?: string | null): string {
  return color || GROUP_PALETTE[groupId % GROUP_PALETTE.length];
}

// Время в строке списка: сегодня — часы, вчера — «вчера», дальше — дата.
export function listTime(iso: string, now = new Date()): string {
  const date = new Date(iso);
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return t("common.yesterday");
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }).replace(".", "");
}

// Таймер ожидания оператора: «6 мин», «1 ч 50 мин» — без слова «ждёт» (решение 4).
export function waitLabelOf(sinceIso: string, now = new Date()): string {
  const minutes = Math.max(0, Math.round((now.getTime() - new Date(sinceIso).getTime()) / 60000));
  if (minutes < 60) return t("time.minutes_short", { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return t("time.days_short", { count: Math.floor(hours / 24) });
  const rest = minutes % 60;
  return rest ? t("time.hours_minutes", { hours, minutes: rest }) : t("time.hours_short", { count: hours });
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
  if (parts.length === 0) return t("conversations.g");
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}

export function conversationName(conversation: ApiConversation): string {
  if (conversation.contact) return conversation.contact.name || t("conversations.guest_number", { id: conversation.contact.id });
  return t("conversations.guest");
}

export function toConversationListItem(conversation: ApiConversation): ConversationListItem {
  const name = conversationName(conversation);
  // avatarBg: стабильно из id контакта.
  const seed = conversation.contact?.id ?? conversation.id;
  return {
    id: conversation.id,
    name,
    initials: initialsOf(name),
    avatarBg: AVATAR_PALETTE[seed % AVATAR_PALETTE.length],
    avatarUrl: conversation.contact?.avatarUrl || undefined,
    channel: PROVIDER_CHANNEL[conversation.connection?.provider ?? "WEB"] ?? "WEB",
    email: conversation.contact?.email ?? "",
    mode: dialogMode(conversation),
    preview:
      conversation.lastMessage?.kind === "voice"
        ? t("conversations.voice_message_duration", { duration: formatPreviewDuration(conversation.lastMessage.durationSeconds ?? 0) })
        : conversation.lastMessage?.kind === "file"
          ? (isImageAttachment(conversation.lastMessage) ? t("common.photo") : t("conversations.file_named", { name: conversation.lastMessage.attachmentName || "" })) + (conversation.lastMessage.text ? ` · ${conversation.lastMessage.text.replace(/\s+/g, " ").slice(0, 60)}` : "")
          : conversation.lastMessage?.text.replace(/\s+/g, " ").slice(0, 80) ?? "—",
    time: listTime(conversation.lastActivityAt),
    unread: conversation.pendingCount ?? 0,
    isMine: conversation.isAssignedToViewer,
    priority: conversation.priority ?? "NONE",
    labels: conversation.labels ?? [],
    agentName: conversation.channel.name,
    agentColor: agentColorOf(conversation.channel.id),
    groupName: conversation.group?.name ?? null,
    groupColor: conversation.group ? groupColorOf(conversation.group.id, conversation.group.color) : "var(--n-5)",
    waitLabel:
      conversation.lifecycle === "OPEN" && conversation.controlMode === "PAUSED"
        ? waitLabelOf(conversation.lastActivityAt)
        : null,
    lastIsOurs: conversation.lastMessage?.author === "OPERATOR" || conversation.lastMessage?.author === "AI",
    lastIsVoice: conversation.lastMessage?.kind === "voice",
  };
}

// Видимость inbox решает backend (ADR-CHATBALLS-0043): группы сотрудника + без группы
// + назначенные ему; владелец и админ видят всё. Фильтры — серверные.
export type ConversationListFilters = Partial<{
  group: string; // id | "none"
  agent: number; // id канала-агента
  assigned: "me" | number;
  waiting: boolean;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  archived: boolean;
  q: string;
}>;

// Запрос окна инбокса: фильтры, порядок и курсор — всё серверное.
export type ConversationListQuery = ConversationListFilters & {
  sort?: ListSort;
  cursor?: number | null;
  limit?: number;
};

export type ConversationWindow = WindowPage<ApiConversation> & { total: number };

export const fetchConversations = (query: ConversationListQuery = {}) => {
  const params = new URLSearchParams();
  if (query.group) params.set("group", query.group);
  if (query.agent) params.set("agent", String(query.agent));
  if (query.assigned) params.set("assigned", String(query.assigned));
  if (query.waiting) params.set("waiting", "1");
  if (query.lifecycle) params.set("lifecycle", query.lifecycle);
  if (query.archived) params.set("archived", "1");
  if (query.q) params.set("q", query.q);
  if (query.sort) params.set("sort", query.sort);
  if (query.cursor) params.set("cursor", String(query.cursor));
  if (query.limit) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return api<ConversationWindow>(`/api/v1/conversations/${suffix}`);
};

// Окно истории: без курсора — хвост переписки; before — вверх по ленте;
// after — то, что появилось после последнего показанного сообщения.
export type MessageWindowQuery = { before?: number | null; after?: number | null; limit?: number };

export const fetchMessages = (conversationId: number, query: MessageWindowQuery = {}) => {
  const params = new URLSearchParams();
  if (query.before) params.set("before", String(query.before));
  if (query.after) params.set("after", String(query.after));
  if (query.limit) params.set("limit", String(query.limit));
  const suffix = params.size ? `?${params.toString()}` : "";
  return api<WindowPage<ApiMessage>>(`/api/v1/conversations/${conversationId}/messages/${suffix}`);
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

// Справочник блока «Диалог» (кадр G): все группы для переноса и коллеги для
// назначения — доступен и сотруднику, у которого нет менеджерских списков.
export type ChatDirectoryEmployee = { id: number; name: string; avatarUrl?: string | null };

export type ChatDirectory = {
  groups: Array<{ id: number; name: string; color?: string }>;
  // Выдача коллег ограничена, поиск — на сервере: ростер организации может
  // быть каким угодно, а выбор ответственного — не список.
  employees: ChatDirectoryEmployee[];
  hasMoreEmployees?: boolean;
};

// Карточка контакта из диалога (карандаш у имени, дизайн-базлайн v2).
export const updateContactCard = (conversationId: number, fields: Partial<{ name: string; description: string; phone: string; company: string; city: string }>) =>
  conversationAction(conversationId, "contact", fields);

export const fetchChatDirectory = (query = "") =>
  api<ChatDirectory>(`/api/v1/conversations/directory/${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ""}`);

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

// Файл из композера («Прикрепить»): multipart file + подпись text.
export const sendFileMessage = (conversationId: number, file: File, caption: string) => {
  const form = new FormData();
  form.append("file", file, file.name);
  if (caption) form.append("text", caption);
  return apiUpload<{ message: ApiMessage }>(`/api/v1/conversations/${conversationId}/attachments/`, form).then((r) => r.message);
};

// --- Онлайн-звонки (SPEC-CHATBALLS-0013): запрос из диалога, ожидание, отмена ---

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
