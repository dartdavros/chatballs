import { avatarColor, channelMap, initialsOf, productMap, relativeTime, type ClientChannelCode, type ClientProductCode } from "../clients/model";

export type ClientDetailTab = "overview" | "dialogs" | "orders" | "ids" | "consent" | "audit";

export const clientDetailTabs: Array<{ key: ClientDetailTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "dialogs", label: "Диалоги" },
  { key: "orders", label: "Продажи" },
  { key: "ids", label: "Идентификаторы каналов" },
  { key: "consent", label: "Consent" },
  { key: "audit", label: "Аудит" },
];

const PROVIDER_TO_CHANNEL: Record<string, ClientChannelCode> = { EMAIL: "EMAIL", MAX: "MAX", TELEGRAM: "TG", WEB: "WEB" };
const PROVIDER_LABEL: Record<string, string> = { EMAIL: "Email", MAX: "MAX", TELEGRAM: "Telegram", WEB: "Web Chat" };
const PAYMENT_LABEL: Record<string, string> = { PENDING: "Ожидает", PAID: "Оплачен", CANCELLED: "Отменён", REFUNDED: "Возврат" };
const FULFILLMENT_LABEL: Record<string, string> = { NONE: "—", PENDING: "В процессе", DELIVERED: "Исполнен", FAILED: "Ошибка" };

const rub = (minor: number) => `₽${Math.round(minor / 100).toLocaleString("ru-RU")}`;

export type ApiClientDetail = {
  id: number;
  cid: string;
  name: string;
  email: string;
  phone: string;
  channels: ClientChannelCode[];
  products: ClientProductCode[];
  openDialogs: number;
  totalDialogs: number;
  ordersCount: number;
  purchasesMinor: number;
  firstContactAt: string;
  lastActivityAt: string;
  dialogs: Array<{ id: number; title: string; channelName: string; provider: string | null; status: string; active: boolean; lastActivityAt: string }>;
  identities: Array<{ provider: string; value: string; createdAt: string }>;
  orders: Array<{ id: number; code: string; product: string; amountMinor: number; currency: string; paymentStatus: string; fulfillmentStatus: string; createdAt: string }>;
  activity: Array<{ type: "created" | "closed"; title: string; at: string }>;
  audit: Array<{ time: string; action: string; object: string; actor: string; result: string }>;
};

export type ClientDetailVm = {
  id: number;
  cid: string;
  name: string;
  initials: string;
  avatarBg: string;
  email: string;
  phone: string;
  channels: Array<{ label: string; color: string; bg: string }>;
  products: Array<{ name: string; color: string; bg: string }>;
  summary: Array<{ label: string; value: string; accent?: boolean; compact?: boolean }>;
  dialogs: Array<{ id: number; title: string; meta: string; status: string; active: boolean; time: string }>;
  identities: Array<{ name: string; value: string; status: string; color: string; bg: string; ok: boolean }>;
  orders: Array<{ id: number; code: string; product: string; amount: string; payment: string; fulfillment: string; date: string }>;
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
    email: api.email || (isGuest ? "без контакта" : "—"),
    phone: api.phone || "—",
    channels: api.channels.map((code) => ({ label: channelMap[code].label, color: channelMap[code].color, bg: channelMap[code].bg })),
    products: api.products.map((code) => ({ name: productMap[code].name, color: productMap[code].color, bg: productMap[code].bg })),
    summary: [
      { label: "Заказы", value: String(api.ordersCount) },
      { label: "Сумма покупок", value: api.purchasesMinor > 0 ? rub(api.purchasesMinor) : "—", accent: api.purchasesMinor > 0 },
      { label: "Диалоги", value: String(api.totalDialogs) },
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
    orders: api.orders.map((order) => ({
      id: order.id,
      code: order.code,
      product: order.product,
      amount: rub(order.amountMinor),
      payment: PAYMENT_LABEL[order.paymentStatus] ?? order.paymentStatus,
      fulfillment: FULFILLMENT_LABEL[order.fulfillmentStatus] ?? order.fulfillmentStatus,
      date: formatDateTime(order.createdAt),
    })),
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
