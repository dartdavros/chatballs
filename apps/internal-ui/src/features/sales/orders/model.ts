import type { SalesFulfillment, SalesOrder, SalesOrdersTab, SalesPayment, StatusBadge, StatusTone } from "./types";

const statusTone = {
  green: { color: "#389e0d", bg: "#f6ffed" },
  amber: { color: "#d48806", bg: "#fffbe6" },
  red: { color: "#cf1322", bg: "#fff2f0" },
  blue: { color: "#0958d9", bg: "#e6f4ff" },
  gray: { color: "#8c8c8c", bg: "#f5f5f5" },
  purple: { color: "#722ed1", bg: "#f9f0ff" },
} satisfies Record<StatusTone, { color: string; bg: string }>;

export const salesOrderTabs: Array<{ key: SalesOrdersTab; label: string }> = [
  { key: "orders", label: "Заказы" },
  { key: "subs", label: "Подписки" },
  { key: "pays", label: "Платежи" },
  { key: "refunds", label: "Возвраты" },
  { key: "exec", label: "Доступ продукта" },
];

export type ApiOrder = {
  id: number;
  code: string;
  contact: { id: number; name: string };
  conversationId: number | null;
  product: { code: string; name: string } | null;
  channel: string | null;
  paymentStatus: "PENDING" | "PAID" | "CANCELLED" | "REFUNDED";
  fulfillmentStatus: "NONE" | "PENDING" | "DELIVERED" | "FAILED";
  amountMinor: number;
  currency: string;
  createdAt: string;
  paidAt: string | null;
  items?: Array<{ id: number; offerCode: string; title: string; quantity: number; amountMinor: number; currency: string }>;
};

const PAYMENT_BADGE: Record<ApiOrder["paymentStatus"], StatusBadge> = {
  PAID: { ...statusTone.green, label: "Оплачен" },
  PENDING: { ...statusTone.amber, label: "Ожидает" },
  CANCELLED: { ...statusTone.gray, label: "Отменён" },
  REFUNDED: { ...statusTone.gray, label: "Возврат" },
};

const FULFILLMENT_BADGE: Record<ApiOrder["fulfillmentStatus"], StatusBadge> = {
  NONE: { ...statusTone.gray, label: "—" },
  PENDING: { ...statusTone.blue, label: "В процессе" },
  DELIVERED: { ...statusTone.green, label: "Исполнен" },
  FAILED: { ...statusTone.red, label: "Ошибка" },
};

export function paymentBadge(status: ApiOrder["paymentStatus"]): StatusBadge {
  return PAYMENT_BADGE[status];
}

export function fulfillmentBadge(status: ApiOrder["fulfillmentStatus"]): StatusBadge {
  return FULFILLMENT_BADGE[status];
}

export const rub = (minor: number) => `₽${Math.round(minor / 100).toLocaleString("ru-RU")}`;

function dateTime(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

const search = (...parts: Array<string | null | undefined>) => parts.filter(Boolean).join(" ").toLowerCase();

export function toOrderRow(order: ApiOrder): SalesOrder & { orderId: number } {
  return {
    orderId: order.id,
    id: order.code,
    date: dateTime(order.createdAt),
    client: order.contact.name,
    offer: order.product ? order.product.name : "—",
    amount: rub(order.amountMinor),
    pay: paymentBadge(order.paymentStatus),
    fulfillment: fulfillmentBadge(order.fulfillmentStatus),
    source: { label: order.channel || "—", color: statusTone.gray.color },
    seller: "—",
    search: search(order.code, order.contact.name, order.product?.name),
  };
}

export function toPaymentRow(order: ApiOrder): SalesPayment {
  return {
    id: order.code,
    order: order.code,
    provider: "—",
    amount: rub(order.amountMinor),
    status: paymentBadge(order.paymentStatus),
    method: "—",
    date: order.paidAt ? dateTime(order.paidAt) : dateTime(order.createdAt),
    reconcile: { color: statusTone.gray.color, label: "—" },
    search: search(order.code, order.contact.name),
  };
}

export function toFulfillmentRow(order: ApiOrder): SalesFulfillment {
  return {
    order: order.code,
    product: order.product ? order.product.name : "—",
    operation: "—",
    status: fulfillmentBadge(order.fulfillmentStatus),
    attempts: "—",
    error: "—",
    updated: dateTime(order.createdAt),
    attention: order.fulfillmentStatus === "FAILED",
    search: search(order.code, order.product?.name),
  };
}
