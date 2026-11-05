import { api } from "../../api/client";
import { t } from "../../i18n";
import type { SiteField } from "./site-fields/model";
import type { WidgetAppearance } from "./appearance/model";
import type { PreChat } from "./pre-chat/model";
import type { ExternalServer } from "./external/types";
import type { SpeechCapabilities, MicrophoneMode } from "@chatballs/contracts";

export type IntegrationProvider = "OPENROUTER" | "CUSTOM" | "DEMO" | "MAX" | "TELEGRAM" | "VK" | "WEB" | "EMAIL" | "MCP" | "HTTP" | "YANDEX_SPEECHKIT";
export type IntegrationKind = "LLM_PROVIDER" | "MESSENGER" | "EXTERNAL_SERVER" | "SPEECH_PROVIDER";
export type IntegrationStatus = "UNCHECKED" | "OK" | "ERROR";
export type WebChatWidgetSummary = {
  id: number;
  code: string;
  publicKey: string;
  name: string;
  status: "DRAFT" | "PUBLISHED" | "DISABLED";
  channel: { id: number; code: string; name: string; groupId?: number | null; hasAgent?: boolean; shared?: boolean } | null;
};

export type Integration = {
  id: number;
  kind: IntegrationKind;
  provider: IntegrationProvider;
  name: string;
  externalServer?: ExternalServer;
  speechCapabilities?: SpeechCapabilities;
  hasSecret: boolean;
  // Публичный префикс ключа + маска («sk-or-••••••••») для колонки «Секрет».
  secretMasked: string;
  isActive: boolean;
  // purpose="notifications" — сервисный бот уведомлений сотрудников (не привязан к каналу продаж).
  // email/imap*/smtp* — Email-подключение (SPEC-CHATBALLS-0025 §3.1).
  config: {
    folderId?: string;
    microphoneMode?: MicrophoneMode;
    maxRecordingBytes?: number;
    maxDictationSeconds?: number;
    fields?: SiteField[];
    preChat?: PreChat;
    siteEvent?: import("@chatballs/contracts").SiteEventRule | null;
    siteEventAvailable?: boolean;
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
    appearance?: WidgetAppearance;
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
  channel: { id: number; code: string; name: string; groupId?: number | null; hasAgent?: boolean; shared?: boolean } | null;
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
  // Статья Центра помощи про этот тип подключения (shared/help).
  helpSlug?: string;
};

export const PROVIDERS: Record<IntegrationProvider, ProviderMeta> = {
  YANDEX_SPEECHKIT: { label: "Yandex SpeechKit", kind: "SPEECH_PROVIDER", secretLabel: t("speech.secret"), defaultBaseUrl: "", hasModel: false, testable: true, checkable: true },
  MCP: { label: t("servers.new_mcp"), kind: "EXTERNAL_SERVER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true, helpSlug: "instrumenty-agenta" },
  HTTP: { label: t("servers.new_http"), kind: "EXTERNAL_SERVER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true, helpSlug: "instrumenty-agenta" },
  OPENROUTER: { label: "OpenRouter", kind: "LLM_PROVIDER", secretLabel: t("settings.api_key"), defaultBaseUrl: "https://openrouter.ai/api/v1", hasModel: true, testable: true, checkable: true },
  // Custom — generic BYOK для любого OpenAI-compatible endpoint (ADR-CHATBALLS-0034).
  // Каталога нет: модель вводится свободным текстом и читается в рантайме.
  CUSTOM: { label: "Custom (OpenAI-compatible)", kind: "LLM_PROVIDER", secretLabel: t("settings.api_key"), defaultBaseUrl: "", hasModel: true, testable: true, checkable: true },
  // Демо-провайдер — живой AI без ключей и сети для знакомства с системой: отвечает по знаниям агента.
  DEMO: { label: t("settings.demo_provider_no_key"), kind: "LLM_PROVIDER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true },
  MAX: { label: "MAX", kind: "MESSENGER", secretLabel: t("settings.bot_token"), defaultBaseUrl: "https://platform-api.max.ru", hasModel: false, testable: true, checkable: true, helpSlug: "max" },
  TELEGRAM: { label: "Telegram", kind: "MESSENGER", secretLabel: t("settings.bot_token"), defaultBaseUrl: "https://api.telegram.org", hasModel: false, testable: true, checkable: true, helpSlug: "telegram" },
  // ВКонтакте — сообщество: секрет это ключ доступа сообщества, идентификатор
  // сообщества подставляет проверка подключения (ADR-CHATBALLS-0020).
  VK: { label: "ВКонтакте", kind: "MESSENGER", secretLabel: t("settings.vk_community_key"), defaultBaseUrl: "https://api.vk.com/method", hasModel: false, testable: true, checkable: true, helpSlug: "vkontakte" },
  WEB: { label: t("common.web_widget"), kind: "MESSENGER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false, checkable: true, helpSlug: "veb-vidzhet" },
  // Email — подключение-ящик IMAP/SMTP (ADR-CHATBALLS-0035); секрет — пароль приложения.
  EMAIL: { label: "Email (IMAP/SMTP)", kind: "MESSENGER", secretLabel: t("common.password"), defaultBaseUrl: "", hasModel: false, testable: true, checkable: true, helpSlug: "pochtovyj-yashchik" },
};

export const STATUS_META: Record<IntegrationStatus, { label: string; bg: string; color: string }> = {
  OK: { label: t("common.connected"), bg: "var(--success-bg)", color: "var(--success-text)" },
  ERROR: { label: t("common.error"), bg: "var(--error-bg)", color: "var(--error-text)" },
  UNCHECKED: { label: t("ai.not_checked"), bg: "var(--n-9)", color: "var(--n-4)" },
};

export const KIND_LABEL: Record<IntegrationKind, string> = {
  SPEECH_PROVIDER: t("speech.stt"),
  EXTERNAL_SERVER: t("ai.tools"),
  LLM_PROVIDER: t("settings.providers"),
  MESSENGER: t("common.connections"),
};

export type ChannelOption = { id: number; code: string; name: string };

export function connectionGroupSettings(initial: Pick<Integration, "channel"> | null, channelId: string, groupId: string): { groupId?: number | null } {
  const ownRoute = initial?.channel?.hasAgent === false && String(initial.channel.id) === channelId;
  return !channelId || ownRoute ? { groupId: groupId ? Number(groupId) : null } : {};
}

// Привязка подключения выбирает агента; id карточки агента = id канала.
export const fetchChannels = () => api<{ items: ChannelOption[] }>("/api/v1/agents/").then((r) => r.items);

export const fetchLlmProviders = () =>
  api<{ items: Integration[] }>("/api/v1/integrations/").then((response) =>
    response.items.filter((item) => item.kind === "LLM_PROVIDER")
  );

export const fetchAgentProviders = () => api<{ items: Integration[] }>("/api/v1/integrations/").then((response) =>
  response.items.filter((item) => item.kind === "LLM_PROVIDER" || item.kind === "SPEECH_PROVIDER"));

// Разрешённые домены Web-виджета. Пустой список в проде
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

// Публичный домен установки для встраивания Web-виджета (SPEC-CHATBALLS-0003 §3).
// Один frontend-образ работает на любом домене (ADR-CHATBALLS-0028 §runtime frontend):
// сниппет генерируется от текущего origin в рантайме, а не от build-time аргумента.
export function webWidgetSnippet(widgetKey: string): string {
  return `<script src="${window.location.origin}/chat-widget.js" data-widget-key="${widgetKey}" async></script>`;
}
