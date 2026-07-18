import { api } from "../../api/client";

export type IntegrationProvider = "OPENROUTER" | "CUSTOM" | "MAX" | "TELEGRAM" | "WEB" | "EMAIL";
export type IntegrationKind = "LLM_PROVIDER" | "MESSENGER";
export type IntegrationStatus = "UNCHECKED" | "OK" | "ERROR";

export type Integration = {
  id: number;
  kind: IntegrationKind;
  provider: IntegrationProvider;
  name: string;
  hasSecret: boolean;
  // purpose="notifications" — сервисный бот уведомлений сотрудников (не привязан к каналу продаж).
  // email/imap*/smtp* — Email-подключение (SPEC-HUB-0025 §3.1).
  config: {
    baseUrl: string;
    defaultModel: string;
    proxyUrl: string;
    botId: string;
    botUsername: string;
    botName: string;
    purpose: string;
    email: string;
    imapHost: string;
    imapPort: number;
    imapSsl: boolean;
    smtpHost: string;
    smtpPort: number;
    smtpSsl: boolean;
  };
  channel: { id: number; code: string; name: string } | null;
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
  // testable — есть секрет для проверки (поле в форме); checkable — доступна кнопка «Проверить»
  // (у Web-виджета секрета нет, но backend проверяет привязку к каналу).
  testable: boolean;
  checkable: boolean;
};

export const PROVIDERS: Record<IntegrationProvider, ProviderMeta> = {
  OPENROUTER: { label: "OpenRouter", kind: "LLM_PROVIDER", secretLabel: "API-ключ", defaultBaseUrl: "https://openrouter.ai/api/v1", hasModel: true, testable: true, checkable: true },
  // Custom — generic BYOK для любого OpenAI-compatible endpoint (ADR-HUB-0034).
  // Каталога нет: модель вводится свободным текстом и читается в рантайме.
  CUSTOM: { label: "Custom (OpenAI-compatible)", kind: "LLM_PROVIDER", secretLabel: "API-ключ", defaultBaseUrl: "", hasModel: true, testable: true, checkable: true },
  MAX: { label: "MAX", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://platform-api.max.ru", hasModel: false, testable: true, checkable: true },
  TELEGRAM: { label: "Telegram", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://api.telegram.org", hasModel: false, testable: true, checkable: true },
  WEB: { label: "Web-виджет", kind: "MESSENGER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true },
  // Email — подключение-ящик IMAP/SMTP (ADR-HUB-0035); секрет — пароль приложения.
  EMAIL: { label: "Email (IMAP/SMTP)", kind: "MESSENGER", secretLabel: "Пароль", defaultBaseUrl: "", hasModel: false, testable: true, checkable: true },
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

export type ChannelOption = { id: number; code: string; name: string };

export const fetchChannels = () => api<{ items: ChannelOption[] }>("/api/v1/channels/").then((r) => r.items);

export const fetchLlmProviders = () =>
  api<{ items: Integration[] }>("/api/v1/integrations/").then((response) =>
    response.items.filter((item) => item.kind === "LLM_PROVIDER")
  );

// Публичный домен Hub для встраивания Web-виджета (SPEC-HUB-0003 §3).
// Один frontend-образ работает на любом домене (ADR-HUB-0028 §runtime frontend):
// сниппет генерируется от текущего origin в рантайме, а не от build-time аргумента.
export function webWidgetSnippet(channelCode: string): string {
  return `<script src="${window.location.origin}/chat-widget.js" data-channel="${channelCode}" async></script>`;
}
