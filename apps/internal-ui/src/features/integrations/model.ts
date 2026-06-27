export type IntegrationProvider = "OPENROUTER" | "MAX" | "TELEGRAM" | "WEB";
export type IntegrationKind = "LLM_PROVIDER" | "MESSENGER";
export type IntegrationStatus = "UNCHECKED" | "OK" | "ERROR";

export type Integration = {
  id: number;
  kind: IntegrationKind;
  provider: IntegrationProvider;
  name: string;
  hasSecret: boolean;
  config: { baseUrl: string; defaultModel: string; botUsername: string };
  status: IntegrationStatus;
  lastCheckedAt: string | null;
  lastError: string;
  createdAt: string;
  updatedAt: string;
};

type ProviderMeta = {
  label: string;
  kind: IntegrationKind;
  secretLabel: string;
  defaultBaseUrl: string;
  hasModel: boolean;
  hasBotName: boolean;
  testable: boolean;
};

export const PROVIDERS: Record<IntegrationProvider, ProviderMeta> = {
  OPENROUTER: { label: "OpenRouter", kind: "LLM_PROVIDER", secretLabel: "API-ключ", defaultBaseUrl: "https://openrouter.ai/api/v1", hasModel: true, hasBotName: false, testable: true },
  MAX: { label: "MAX", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://platform-api2.max.ru", hasModel: false, hasBotName: true, testable: true },
  TELEGRAM: { label: "Telegram", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://api.telegram.org", hasModel: false, hasBotName: true, testable: true },
  WEB: { label: "Web-виджет", kind: "MESSENGER", secretLabel: "", defaultBaseUrl: "", hasModel: false, hasBotName: false, testable: false },
};

export const STATUS_META: Record<IntegrationStatus, { label: string; bg: string; color: string }> = {
  OK: { label: "Подключено", bg: "#f6ffed", color: "#389e0d" },
  ERROR: { label: "Ошибка", bg: "#fff1f0", color: "#cf1322" },
  UNCHECKED: { label: "Не проверено", bg: "#f5f5f5", color: "#8c8c8c" },
};

export const KIND_LABEL: Record<IntegrationKind, string> = {
  LLM_PROVIDER: "Провайдеры",
  MESSENGER: "Подключения",
};
