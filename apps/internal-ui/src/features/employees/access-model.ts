import type { AccessProfile, CapabilityDefinition, ScopeType } from "../../types";

const DOMAIN_LABELS: Record<string, string> = {
  ai: "AI",
  audit: "Настройки и аудит",
  company: "Компания",
  conversations: "Диалоги",
  customers: "Клиенты",
  departments: "Отделы",
  employees: "Сотрудники",
  integrations: "Интеграции",
  notifications: "Уведомления",
  ownership: "Сотрудники",
  products: "Продукты",
  sales: "Продажи",
  sales_sources: "Продажи",
  secrets: "Интеграции",
  settings: "Настройки и аудит",
  support: "Поддержка",
};

const DOMAIN_ORDER = [
  "Компания", "Отделы", "Сотрудники", "Продукты", "AI", "Интеграции",
  "Настройки и аудит", "Диалоги", "Клиенты", "Продажи", "Поддержка", "Уведомления",
];

export function groupCapabilities(items: CapabilityDefinition[]) {
  const groups = new Map<string, CapabilityDefinition[]>();
  for (const item of items) {
    const domain = DOMAIN_LABELS[item.code.split(".")[0]] ?? item.code.split(".")[0];
    groups.set(domain, [...(groups.get(domain) ?? []), item]);
  }
  return [...groups.entries()]
    .sort(([left], [right]) => DOMAIN_ORDER.indexOf(left) - DOMAIN_ORDER.indexOf(right))
    .map(([domain, capabilities]) => ({ domain, capabilities }));
}

export function formatScopes(scopes: ScopeType[]) {
  const labels = scopes.map((scope) => scope === "DEPARTMENT" ? "Отдел" : "Организация");
  return labels.join(", ") || "—";
}

export function editableProfile(profile: AccessProfile | null) {
  return Boolean(profile && !profile.isSystem && profile.isActive);
}
