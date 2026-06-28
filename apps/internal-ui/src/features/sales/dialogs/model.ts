import { api } from "../../../api/client";
import type { ChannelKey, ControlMode, DialogMode, SalesDialog } from "./types";

export type ApiMessage = { id: number; author: "CONTACT" | "AI" | "OPERATOR" | "SYSTEM"; text: string; createdAt: string };

export type HistoryItem = {
  id: number;
  channelName: string;
  provider: "MAX" | "TELEGRAM" | "WEB" | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  createdAt: string;
  lastActivityAt: string;
  preview: string;
};

export type ApiConversation = {
  id: number;
  channel: { code: string; name: string; product: { code: string; name: string } | null };
  connection: { id: number; provider: "MAX" | "TELEGRAM" | "WEB"; name: string } | null;
  contact: { id: number; name: string };
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  controlMode: "AI" | "HUMAN" | "PAUSED";
  expectedResponder: string;
  assignedOperatorId: number | null;
  lastActivityAt: string;
  createdAt: string;
  lastMessage: ApiMessage | null;
  pendingCount?: number;
  messages?: ApiMessage[];
  history?: HistoryItem[];
};

const AVATAR_PALETTE = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4413b", "#6b5be0"];
const PROVIDER_CHANNEL: Record<string, ChannelKey> = { MAX: "MAX", TELEGRAM: "TG", WEB: "WEB" };

export function controlModeOf(conversation: ApiConversation): ControlMode {
  if (conversation.controlMode === "HUMAN") return "human";
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

export function toDialog(conversation: ApiConversation): SalesDialog {
  const name = conversation.contact.name || `Гость ${conversation.contact.id}`;
  return {
    id: conversation.id,
    name,
    initials: initialsOf(name),
    avatarBg: AVATAR_PALETTE[conversation.contact.id % AVATAR_PALETTE.length],
    product: conversation.channel.name,
    channel: PROVIDER_CHANNEL[conversation.connection?.provider ?? "WEB"] ?? "WEB",
    mode: dialogMode(conversation),
    preview: conversation.lastMessage?.text.replace(/\s+/g, " ").slice(0, 80) ?? "—",
    time: new Date(conversation.lastActivityAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }),
    unread: conversation.pendingCount ?? 0,
  };
}

export const fetchConversations = () => api<{ items: ApiConversation[] }>("/api/v1/conversations/").then((r) => r.items);
export const fetchConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/`).then((r) => r.conversation);
export const claimConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/claim/`, { method: "POST" }).then((r) => r.conversation);
export const releaseConversation = (id: number) => api<{ conversation: ApiConversation }>(`/api/v1/conversations/${id}/release/`, { method: "POST" }).then((r) => r.conversation);
export const sendOperatorMessage = (id: number, text: string) => api(`/api/v1/conversations/${id}/messages/`, { method: "POST", body: JSON.stringify({ text }) });
