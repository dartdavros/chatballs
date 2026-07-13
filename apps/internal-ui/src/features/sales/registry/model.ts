import type { StatusBadge, StatusTone } from "../orders/types";

// Единый реестр продаж (SPEC-HUB-0014 §8.1). Проекция Sale из /api/v1/sales/.
// Источник истины о продаже — backend продукта; Hub ведёт учёт и атрибуцию.

const statusTone: Record<StatusTone, { color: string; bg: string }> = {
  green: { color: "#389e0d", bg: "#f6ffed" },
  amber: { color: "#d48806", bg: "#fffbe6" },
  red: { color: "#cf1322", bg: "#fff2f0" },
  blue: { color: "#0958d9", bg: "#e6f4ff" },
  gray: { color: "#8c8c8c", bg: "#f5f5f5" },
  purple: { color: "#722ed1", bg: "#f9f0ff" },
};

export type SaleStatus = "CONFIRMED" | "PARTIALLY_REFUNDED" | "REFUNDED" | "CANCELLED";
export type SaleSourceType = "PRODUCT_API" | "MANUAL" | "LEGACY_IMPORT";
export type SaleEventType =
  | "sale.confirmed"
  | "sale.corrected"
  | "sale.cancelled"
  | "sale.partially_refunded"
  | "sale.refunded"
  | "sale.legacy_imported";
export type AttributionMethod = "ATTRIBUTION_TOKEN" | "EXTERNAL_IDENTITY" | "CONTACT_MATCH" | "MANUAL" | "NONE";
export type ActorType = "AI_AGENT" | "EMPLOYEE" | "OPERATOR" | "OWNER" | "";

export type ApiSaleEvent = {
  id: number;
  eventType: SaleEventType;
  sourceType: SaleSourceType;
  schemaVersion: number;
  occurredAt: string | null;
  receivedAt: string | null;
  appliedAt: string | null;
  processingStatus: "RECEIVED" | "APPLIED" | "REJECTED" | "RETRYABLE";
  processingError: string;
  actor: { id: number; name: string } | null;
};

export type ApiSale = {
  id: number;
  product: { code: string; name: string } | null;
  environment: "LOCAL" | "STAGING" | "PRODUCTION";
  sourceType: SaleSourceType;
  externalSaleId: string;
  externalCustomerId: string;
  contact: { id: number; name: string } | null;
  conversationId: number | null;
  status: SaleStatus;
  amountMinor: number;
  refundedAmountMinor: number;
  netAmountMinor: number;
  currency: string;
  occurredAt: string | null;
  lastEventAt: string | null;
  attributionMethod: AttributionMethod;
  attributedActor: { type: ActorType; id: string } | null;
  source: { id: number; code: string } | null;
  lineItems: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  events?: ApiSaleEvent[];
};

const STATUS_BADGE: Record<SaleStatus, StatusBadge> = {
  CONFIRMED: { ...statusTone.green, label: "Подтверждена" },
  PARTIALLY_REFUNDED: { ...statusTone.amber, label: "Частичный возврат" },
  REFUNDED: { ...statusTone.gray, label: "Возврат" },
  CANCELLED: { ...statusTone.gray, label: "Отменена" },
};

const SOURCE_BADGE: Record<SaleSourceType, StatusBadge> = {
  PRODUCT_API: { ...statusTone.blue, label: "Product API" },
  MANUAL: { ...statusTone.purple, label: "Ручная" },
  LEGACY_IMPORT: { ...statusTone.gray, label: "Legacy import" },
};

const ATTRIBUTION_LABEL: Record<AttributionMethod, string> = {
  ATTRIBUTION_TOKEN: "Токен диалога",
  EXTERNAL_IDENTITY: "External identity",
  CONTACT_MATCH: "Совпадение контакта",
  MANUAL: "Ручная привязка",
  NONE: "Без атрибуции",
};

const ACTOR_LABEL: Record<Exclude<ActorType, "">, string> = {
  AI_AGENT: "AI-агент",
  OPERATOR: "Оператор",
  EMPLOYEE: "Сотрудник",
  OWNER: "Владелец",
};

export const EVENT_TYPE_LABEL: Record<SaleEventType, string> = {
  "sale.confirmed": "Подтверждение",
  "sale.corrected": "Исправление",
  "sale.cancelled": "Отмена",
  "sale.partially_refunded": "Частичный возврат",
  "sale.refunded": "Возврат",
  "sale.legacy_imported": "Импорт legacy",
};

export const statusBadge = (status: SaleStatus): StatusBadge => STATUS_BADGE[status];
export const sourceBadge = (source: SaleSourceType): StatusBadge => SOURCE_BADGE[source];
export const attributionLabel = (method: AttributionMethod): string => ATTRIBUTION_LABEL[method];

export function actorView(actor: ApiSale["attributedActor"]): { label: string; ai: boolean } {
  if (!actor || !actor.type) return { label: "—", ai: false };
  return { label: ACTOR_LABEL[actor.type], ai: actor.type === "AI_AGENT" };
}

export function money(minor: number, currency: string): string {
  const sign = currency === "RUB" ? "₽" : `${currency} `;
  return `${sign}${Math.round(minor / 100).toLocaleString("ru-RU")}`;
}

export function dateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export function dateTimeLong(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export type SaleRow = {
  saleId: number;
  external: string;
  date: string;
  client: string;
  product: string;
  amount: string;
  refund: string;
  net: string;
  status: StatusBadge;
  source: StatusBadge;
  attribution: string;
  actor: { label: string; ai: boolean };
  conversationId: number | null;
  synced: string;
  search: string;
};

const search = (...parts: Array<string | null | undefined>) => parts.filter(Boolean).join(" ").toLowerCase();

export function toSaleRow(sale: ApiSale): SaleRow {
  return {
    saleId: sale.id,
    external: sale.externalSaleId || `#${sale.id}`,
    date: dateTime(sale.occurredAt),
    client: sale.contact ? sale.contact.name : "—",
    product: sale.product ? sale.product.name : "—",
    amount: money(sale.amountMinor, sale.currency),
    refund: sale.refundedAmountMinor > 0 ? money(sale.refundedAmountMinor, sale.currency) : "—",
    net: money(sale.netAmountMinor, sale.currency),
    status: statusBadge(sale.status),
    source: sourceBadge(sale.sourceType),
    attribution: attributionLabel(sale.attributionMethod),
    actor: actorView(sale.attributedActor),
    conversationId: sale.conversationId,
    synced: dateTime(sale.lastEventAt),
    search: search(sale.externalSaleId, sale.contact?.name, sale.product?.name, sale.externalCustomerId),
  };
}
