import type { SessionUser } from "../../types";
import { hasCapability } from "../../auth/access";

// Аудит живёт на своём экране (AuditPage) и своём хуке; useAdministration
// остался только под «Организацию» в Настройках.
export type AdministrationSection = "organization";

export type OrganizationSettings = {
  name: string;
  timezone: string;
  currency: string;
  logoUrl: string | null;
  // Когда настройки сохраняли в последний раз — подпись у кнопки (кадр N1).
  updatedAt: string | null;
};

export type AuditResult = "SUCCESS" | "DENIED" | "FAILED";

export type AuditEvent = {
  id: number;
  createdAt: string;
  actorId: number | null;
  actor: string;
  actorEmail: string;
  // Код действия и подпись приходят вместе: подписи может не быть, тогда
  // показываем код — по нему видно, что произошло.
  action: string;
  actionLabel: string;
  category: string;
  categoryLabel: string;
  object: string;
  objectType: string;
  objectId: string;
  result: AuditResult;
  resultLabel: string;
  sourceIp: string;
  correlationId: string;
  details: Record<string, unknown>;
};

export type AuditFilterOption = { value: string; label: string };

export type AuditPeriod = "today" | "7d" | "30d" | "90d" | "all";

export type AuditQuery = {
  q: string;
  period: AuditPeriod;
  category: string;
  actor: string;
  result: string;
  page: number;
};

export type AuditPayload = {
  items: AuditEvent[];
  page: number;
  pageSize: number;
  pageCount: number;
  total: number;
  filters: {
    categories: AuditFilterOption[];
    results: AuditFilterOption[];
    actors: AuditFilterOption[];
  };
};

export const AUDIT_PERIODS: Array<[AuditPeriod, string]> = [
  ["today", "Сегодня"],
  ["7d", "7 дней"],
  ["30d", "30 дней"],
  ["90d", "90 дней"],
  ["all", "Всё время"],
];

export const EMPTY_AUDIT_QUERY: AuditQuery = {
  q: "",
  period: "30d",
  category: "",
  actor: "",
  result: "",
  page: 1,
};

export function auditQueryIsDirty(query: AuditQuery): boolean {
  return query.q.trim() !== ""
    || query.period !== EMPTY_AUDIT_QUERY.period
    || query.category !== ""
    || query.actor !== ""
    || query.result !== "";
}

export function canManageSettings(user: SessionUser): boolean {
  return hasCapability(user, "settings.manage");
}
