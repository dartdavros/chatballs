import { api } from "../../api/client";

export type IntegrationProvider = "OPENROUTER" | "CUSTOM" | "DEMO" | "MAX" | "TELEGRAM" | "WEB" | "EMAIL";
export type IntegrationKind = "LLM_PROVIDER" | "MESSENGER";
export type IntegrationStatus = "UNCHECKED" | "OK" | "ERROR";
export type WebChatWidgetSummary = {
  id: number;
  code: string;
  publicKey: string;
  name: string;
  status: "DRAFT" | "PUBLISHED" | "DISABLED";
  channel: { id: number; code: string; name: string } | null;
};

export type Integration = {
  id: number;
  kind: IntegrationKind;
  provider: IntegrationProvider;
  name: string;
  hasSecret: boolean;
  // Публичный префикс ключа + маска («sk-or-••••••••») для колонки «Секрет».
  secretMasked: string;
  isActive: boolean;
  // purpose="notifications" — сервисный бот уведомлений сотрудников (не привязан к каналу продаж).
  // email/imap*/smtp* — Email-подключение (SPEC-CHATBALLS-0025 §3.1).
  config: {
    baseUrl: string;
    defaultModel: string;
    transcriptionModel: string;
    proxyUrl: string;
    botId: string;
    botUsername: string;
    botName: string;
    purpose: string;
    allowedOrigins: string[];
    title: string;
    accent: string;
    greeting: string;
    quickReplies: string[];
    consentText: string;
    consentVersion: string;
    email: string;
    imapHost: string;
    imapPort: number;
    imapSsl: boolean;
    smtpHost: string;
    smtpPort: number;
    smtpSsl: boolean;
  };
  channel: { id: number; code: string; name: string } | null;
  webChatWidget?: WebChatWidgetSummary | null;
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
  // Custom — generic BYOK для любого OpenAI-compatible endpoint (ADR-CHATBALLS-0034).
  // Каталога нет: модель вводится свободным текстом и читается в рантайме.
  CUSTOM: { label: "Custom (OpenAI-compatible)", kind: "LLM_PROVIDER", secretLabel: "API-ключ", defaultBaseUrl: "", hasModel: true, testable: true, checkable: true },
  // Демо-провайдер — живой AI без ключей и сети для знакомства с системой: отвечает по знаниям агента.
  DEMO: { label: "Демо-провайдер (без ключа)", kind: "LLM_PROVIDER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true },
  MAX: { label: "MAX", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://platform-api.max.ru", hasModel: false, testable: true, checkable: true },
  TELEGRAM: { label: "Telegram", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://api.telegram.org", hasModel: false, testable: true, checkable: true },
  WEB: { label: "Web-виджет", kind: "MESSENGER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true },
  // Email — подключение-ящик IMAP/SMTP (ADR-CHATBALLS-0035); секрет — пароль приложения.
  EMAIL: { label: "Email (IMAP/SMTP)", kind: "MESSENGER", secretLabel: "Пароль", defaultBaseUrl: "", hasModel: false, testable: true, checkable: true },
};

export const STATUS_META: Record<IntegrationStatus, { label: string; bg: string; color: string }> = {
  OK: { label: "Подключено", bg: "var(--success-bg)", color: "var(--success-text)" },
  ERROR: { label: "Ошибка", bg: "var(--error-bg)", color: "var(--error-text)" },
  UNCHECKED: { label: "Не проверено", bg: "var(--n-9)", color: "var(--n-4)" },
};

export const KIND_LABEL: Record<IntegrationKind, string> = {
  LLM_PROVIDER: "Провайдеры",
  MESSENGER: "Подключения",
};

export type ChannelOption = { id: number; code: string; name: string };

// Привязка подключения выбирает агента; id карточки агента = id канала.
export const fetchChannels = () => api<{ items: ChannelOption[] }>("/api/v1/agents/").then((r) => r.items);

export const fetchLlmProviders = () =>
  api<{ items: Integration[] }>("/api/v1/integrations/").then((response) =>
    response.items.filter((item) => item.kind === "LLM_PROVIDER")
  );

// Разрешённые домены Web-виджета (SPEC-HUB-0010 §7.1). Пустой список в проде
// запрещает все origin'ы, поэтому домены вводятся руками и обязательны.
// Принимаем три формы, которые понимает backend (webchat.services.origin_allowed):
// `example.com`, `*.example.com` и `https://example.com:8443`; `localhost` — для разработки.
const ORIGIN_RULE = /^(?:https?:\/\/)?(?:\*\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*(?::\d{1,5})?$/i;

// Ввод — свободный текст: домены разделяются запятой, точкой с запятой или переносом.
export function parseAllowedOrigins(input: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of input.split(/[\s,;]+/)) {
    const item = raw.trim().replace(/\/+$/, "");
    const key = item.toLowerCase();
    if (!item || seen.has(key)) continue;
    seen.add(key);
    result.push(item);
  }
  return result;
}

export const formatAllowedOrigins = (origins: string[]): string => origins.join(", ");

// Возвращает первый непонятный домен — форма показывает его в ошибке поля.
export const invalidAllowedOrigin = (origins: string[]): string | undefined =>
  origins.find((item) => !ORIGIN_RULE.test(item));

// Публичный домен Hub для встраивания Web-виджета (SPEC-CHATBALLS-0003 §3).
// Один frontend-образ работает на любом домене (ADR-CHATBALLS-0028 §runtime frontend):
// сниппет генерируется от текущего origin в рантайме, а не от build-time аргумента.
export function webWidgetSnippet(widgetKey: string): string {
  return `<script src="${window.location.origin}/chat-widget.js" data-widget-key="${widgetKey}" async></script>`;
}
