import { api } from "../../api/client";
import type { ChannelKey, ConversationListItem, ControlMode, DialogMode } from "./types";

// kind: "" — текст, "contact_request" — запрос контакта, "contact" — клиент поделился номером.
export type ApiMessage = { id: number; author: "CONTACT" | "AI" | "OPERATOR" | "SYSTEM"; kind?: string; text: string; contentHtml?: string; createdAt: string };

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
  lastActivityAt: string;
  createdAt: string;
  lastMessage: ApiMessage | null;
  pendingCount?: number;
  messages?: ApiMessage[];
  history?: HistoryItem[];
};

const AVATAR_PALETTE = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4413b", "#6b5be0"];
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
    preview: conversation.lastMessage?.text.replace(/\s+/g, " ").slice(0, 80) ?? "—",
    time: new Date(conversation.lastActivityAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }),
    unread: conversation.pendingCount ?? 0,
  };
}

// department — изоляция inbox (§10): sales/support оператор видит только свой отдел.
export const fetchConversations = (department: "sales" | "support") =>
  api<{ items: ApiConversation[] }>(`/api/v1/conversations/?department=${department}`).then((r) => r.items);
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

// --- Онлайн-звонки (SPEC-HUB-0013): запрос из диалога, ожидание, отмена ---

export type ApiCall = {
  id: string;
  conversationId: number;
  status: "REQUESTED" | "RINGING" | "ACCEPTED" | "CONNECTING" | "ACTIVE" | "DECLINED" | "CANCELLED" | "MISSED" | "ENDED" | "FAILED" | "EXPIRED";
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
export const requestCall = (conversationId: number) =>
  api<{ call: ApiCall; staffAccessToken: string; iceServers: RTCIceServer[] }>(`/api/v1/calls/conversations/${conversationId}/`, { method: "POST" })
    .then((r): CreatedCall => ({ call: r.call, access: { accessToken: r.staffAccessToken, iceServers: r.iceServers } }));
export const fetchActiveCall = (conversationId: number) =>
  api<{ call: ApiCall | null }>(`/api/v1/calls/conversations/${conversationId}/active/`).then((r) => r.call);
export const fetchCall = (callId: string) => api<{ call: ApiCall }>(`/api/v1/calls/${callId}/`).then((r) => r.call);
export const cancelCall = (callId: string) => api<{ call: ApiCall }>(`/api/v1/calls/${callId}/cancel/`, { method: "POST" }).then((r) => r.call);
export const fetchStaffCallAccess = (callId: string) =>
  api<{ accessToken: string; iceServers: RTCIceServer[] }>(`/api/v1/calls/${callId}/access-token/`, { method: "POST" });
