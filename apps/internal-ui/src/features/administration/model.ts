import type { RouteKey, SessionUser } from "../../types";
import { hasCapability } from "../../auth/access";

export type AdministrationRoute = Extract<
  RouteKey,
  "administrationOrganization" | "administrationSubscription" | "administrationAudit"
>;

export type AdministrationSection = "organization" | "subscription" | "audit";

export type OrganizationSettings = {
  name: string;
  timezone: string;
  currency: string;
  logoUrl: string | null;
};

export type SubscriptionQuota = {
  key: string;
  label: string;
  mode: string;
  limit: number | null;
  used: number;
  unit: string;
};

export type SubscriptionSummary = {
  planCode: string;
  planName: string;
  status: string;
  aiAgentQuantity: number;
  monthlyChargeMinor: number;
  currency: string;
  periodStart: string | null;
  periodEnd: string | null;
  quotas: SubscriptionQuota[];
};

export type AuditEvent = {
  id: number;
  createdAt: string;
  actor: string;
  action: string;
  result: "SUCCESS" | "DENIED" | "FAILED";
  resultLabel: string;
};

export function administrationSection(route: AdministrationRoute): AdministrationSection {
  if (route === "administrationSubscription") return "subscription";
  if (route === "administrationAudit") return "audit";
  return "organization";
}

export function canManageSettings(user: SessionUser): boolean {
  return hasCapability(user, "settings.manage");
}

export function formatMoney(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amountMinor / 100);
}

export function formatQuotaValue(value: number, unit: string): string {
  if (unit === "bytes") {
    if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} ГБ`;
    return `${(value / 1024 ** 2).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} МБ`;
  }
  return value.toLocaleString("ru-RU");
}

const SUBSCRIPTION_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Активен",
  CANCELLED: "Завершён",
  GRACE_PERIOD: "Льготный период",
  PENDING_PAYMENT: "Ожидает оплаты",
  SUSPENDED: "Приостановлен",
};

export function subscriptionStatusLabel(status: string): string {
  return SUBSCRIPTION_STATUS_LABELS[status] ?? "Не определён";
}
