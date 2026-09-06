import { avatarColor, channelMap, initialsOf, productStyle, relativeTime, type ClientChannelCode, type ClientProductRef } from "../clients/model";

export type ClientDetailTab = "overview" | "dialogs" | "ids" | "consent" | "audit";

export const clientDetailTabs: Array<{ key: ClientDetailTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "dialogs", label: "Диалоги" },
  { key: "ids", label: "Идентификаторы каналов" },
  { key: "consent", label: "Согласие" },
  { key: "audit", label: "Аудит" },
];

const PROVIDER_TO_CHANNEL: Record<string, ClientChannelCode> = { EMAIL: "EMAIL", MAX: "MAX", TELEGRAM: "TG", WEB: "WEB" };
const PROVIDER_LABEL: Record<string, string> = { EMAIL: "Email", MAX: "MAX", TELEGRAM: "Telegram", WEB: "Web Chat" };

export type ApiClientDetail = {
  id: number;
  cid: string;
  name: string;
  avatarUrl?: string;
  description?: string;
  company?: string;
  city?: string;
  email: string;
  phone: string;
  channels: ClientChannelCode[];
  products: ClientProductRef[];
  openDialogs: number;
  totalDialogs: number;
  firstContactAt: string;
  lastActivityAt: string;
  dialogs: Array<{ id: number; title: string; channelName: string; provider: string | null; status: string; active: boolean; lastActivityAt: string }>;
  identities: Array<{ provider: string; value: string; createdAt: string }>;
  activity: Array<{ type: "created" | "closed"; title: string; at: string }>;
  audit: Array<{ time: string; action: string; object: string; actor: string; result: string }>;
};

export type ClientDetailVm = {
  id: number;
  cid: string;
  name: string;
  initials: string;
  avatarBg: string;
  avatarUrl: string;
  description: string;
  company: string;
  city: string;
  email: string;
  phone: string;
  rawPhone: string;
  channels: Array<{ label: string; color: string; bg: string }>;
  products: Array<{ name: string; color: string; bg: string }>;
  summary: Array<{ label: string; value: string; accent?: boolean; compact?: boolean }>;
  dialogs: Array<{ id: number; title: string; meta: string; status: string; active: boolean; time: string }>;
  identities: Array<{ name: string; value: string; status: string; color: string; bg: string; ok: boolean }>;
  activity: Array<{ title: string; time: string; color: string }>;
  audit: Array<{ time: string; action: string; object: string; actor: string; result: string }>;
};

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(iso));
}

function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export function toClientDetailVm(api: ApiClientDetail): ClientDetailVm {
  const isGuest = /гость/i.test(api.name);
  return {
    id: api.id,
    cid: api.cid,
    name: api.name,
    initials: initialsOf(api.name),
    avatarBg: isGuest ? "#8c8c8c" : avatarColor(api.cid),
    avatarUrl: api.avatarUrl ?? "",
    description: api.description ?? "",
    company: api.company ?? "",
    city: api.city ?? "",
    email: api.email || (isGuest ? "без контакта" : "—"),
    phone: api.phone || "—",
    rawPhone: api.phone ?? "",
    channels: api.channels.map((code) => ({ label: channelMap[code].label, color: channelMap[code].color, bg: channelMap[code].bg })),
    products: api.products.map((product) => ({ name: product.name, ...productStyle(product.code) })),
    summary: [
      { label: "Диалоги", value: String(api.totalDialogs) },
      { label: "Открытые", value: String(api.openDialogs) },
      { label: "Первый контакт", value: formatDate(api.firstContactAt), compact: true },
    ],
    dialogs: api.dialogs.map((dialog) => ({
      id: dialog.id,
      title: dialog.title,
      meta: [dialog.channelName, dialog.provider ? PROVIDER_LABEL[dialog.provider] ?? dialog.provider : null].filter(Boolean).join(" · "),
      status: dialog.status,
      active: dialog.active,
      time: relativeTime(dialog.lastActivityAt).label,
    })),
    identities: api.identities.map((identity) => {
      const code = PROVIDER_TO_CHANNEL[identity.provider];
      const meta = code ? channelMap[code] : { color: "#8c8c8c", bg: "#f5f5f5" };
      return {
        name: PROVIDER_LABEL[identity.provider] ?? identity.provider,
        value: identity.value,
        status: `с ${formatDate(identity.createdAt)}`,
        color: meta.color,
        bg: meta.bg,
        ok: true,
      };
    }),
    activity: api.activity.map((event) => ({
      title: event.title,
      time: formatDateTime(event.at),
      color: event.type === "closed" ? "#722ed1" : "#1677ff",
    })),
    audit: api.audit.map((event) => ({
      time: formatDateTime(event.time),
      action: event.action,
      object: event.object,
      actor: event.actor,
      result: event.result,
    })),
  };
}
