// Список контактов (дизайн-базлайн v2, кадры K1/K2): контакт · как связаться ·
// каналы · последний диалог · открытые. Коммерции здесь нет — колонка
// «Продукты» и фильтр по продуктам убраны (ADR-CHATBALLS-0041).

import { waitLabelOf } from "../../conversations/model";
import { channelMap } from "../../../shared/providers";
import { shortDate } from "../../../shared/utils";

export { channelMap };

export type ClientChannelCode = "EMAIL" | "MAX" | "TG" | "WEB";
export type ClientSortKey = "last" | "open";
export type ClientDropdown = "agents" | "channels";
export type ClientAgentRef = { id: number; code: string; name: string };

export type SalesClient = {
  id: number;
  name: string;
  initials: string;
  avatarUrl: string;
  avatarBg: string;
  cid: string;
  phone: string;
  email: string;
  username: string;
  anon?: boolean;
  channels: ClientChannelCode[];
  agents: ClientAgentRef[];
  last: number;
  lastAt: string;
  mode: "wait" | "ai" | "operator" | "closed";
  lastAgentName: string;
  lastAssignee: string;
  openDialogs: number;
};

export type SalesClientRowVm = Omit<SalesClient, "channels"> & {
  lastDot: string;
  lastWho: string;
  lastWhen: string;
  openColor: string;
  contactLine: string;
  contactSub: string;
  channels: Array<{ code: ClientChannelCode; full: string; color: string; bg: string }>;
};

export const channelOptions: Array<{ code: ClientChannelCode; name: string; color: string }> = [
  { code: "EMAIL", name: "Email", color: channelMap.EMAIL.color },
  { code: "MAX", name: "MAX", color: channelMap.MAX.color },
  { code: "TG", name: "Telegram", color: channelMap.TG.color },
  { code: "WEB", name: "Web-виджет", color: channelMap.WEB.color },
];


const statusDot = {
  wait: "#faad14",
  ai: "var(--ai)",
  operator: "var(--primary)",
  closed: "var(--n-5)",
} satisfies Record<SalesClient["mode"], string>;

// Реальный контакт с бэкенда (conversations/clients.py).
export type ApiClient = {
  id: number;
  avatarUrl?: string;
  cid: string;
  name: string;
  phone: string;
  email: string;
  username: string;
  channels: ClientChannelCode[];
  agents: ClientAgentRef[];
  openDialogs: number;
  totalDialogs: number;
  lastActivityAt: string;
  mode: SalesClient["mode"];
  lastAgentName: string;
  lastAgentCode: string;
  lastAssignee: string;
};

const AVATAR_COLORS = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4456b", "#4c6ef0", "#7048b6"];

export function initialsOf(name: string): string {
  const words = name.replace(/·.*/, "").trim().split(/\s+/).filter(Boolean);
  const letters = words.slice(0, 2).map((word) => word[0]).join("");
  return (letters || name.slice(0, 2)).toUpperCase();
}

export function avatarColor(seed: string): string {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

export function relativeTime(iso: string): { minutes: number; label: string } {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 60) return { minutes, label: `${minutes} мин назад` };
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { minutes, label: `${hours} ч назад` };
  return { minutes, label: `${Math.floor(hours / 24)} д назад` };
}

// «17:10 · сегодня» · «вчера, 18:02» · «3 сен» (кадр K1).
export function contactTime(iso: string, now = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const time = date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const days = Math.round((startOfDay(now).getTime() - startOfDay(date).getTime()) / 86400000);
  if (days === 0) return `${time} · сегодня`;
  if (days === 1) return `вчера, ${time}`;
  return shortDate(date);
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

// Кто ведёт последний диалог (кадр K1): AI с именем агента, ожидание с
// таймером, сотрудник по имени, закрытый — кем закрыт.
export function lastDialogWho(client: SalesClient): string {
  if (client.mode === "ai") return `AI · ${client.lastAgentName}`;
  if (client.mode === "wait") return `Ждёт человека · ${waitLabelOf(client.lastAt)}`;
  if (client.mode === "operator") return client.lastAssignee || "Ведёт сотрудник";
  return `Закрыт · ${client.lastAssignee || "AI"}`;
}

export function toSalesClient(api: ApiClient): SalesClient {
  const isGuest = /гость/i.test(api.name);
  const { minutes } = relativeTime(api.lastActivityAt);
  return {
    id: api.id,
    name: api.name,
    initials: initialsOf(api.name),
    avatarUrl: api.avatarUrl ?? "",
    avatarBg: isGuest ? "var(--n-4)" : avatarColor(api.cid),
    cid: api.cid,
    phone: api.phone,
    email: api.email,
    username: api.username,
    anon: isGuest,
    channels: api.channels,
    agents: api.agents ?? [],
    last: minutes,
    lastAt: api.lastActivityAt,
    mode: api.mode,
    lastAgentName: api.lastAgentName ?? "",
    lastAssignee: api.lastAssignee ?? "",
    openDialogs: api.openDialogs,
  };
}

export function toSalesClientRow(client: SalesClient): SalesClientRowVm {
  // «Как связаться»: телефон или email первой строкой, второй — логин либо
  // оставшийся контакт; у анонимной сессии виджета контактов нет.
  const contactLine = client.phone || client.email || "—";
  const contactSub = client.phone && client.email
    ? client.email
    : client.username
      ? `@${client.username}`
      : client.anon
        ? "анонимная сессия виджета"
        : "";
  return {
    ...client,
    channels: client.channels.map((code) => ({ code, ...channelMap[code] })),
    lastDot: statusDot[client.mode],
    lastWho: lastDialogWho(client),
    lastWhen: contactTime(client.lastAt),
    contactLine,
    contactSub,
    openColor: client.openDialogs > 0 ? "var(--warning-text)" : "var(--n-5)",
  };
}
