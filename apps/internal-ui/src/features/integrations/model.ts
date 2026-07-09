import { api } from "../../api/client";

export type IntegrationProvider = "OPENROUTER" | "MAX" | "TELEGRAM" | "WEB";
export type IntegrationKind = "LLM_PROVIDER" | "MESSENGER";
export type IntegrationStatus = "UNCHECKED" | "OK" | "ERROR";

export type Integration = {
  id: number;
  kind: IntegrationKind;
  provider: IntegrationProvider;
  name: string;
  hasSecret: boolean;
  config: { baseUrl: string; defaultModel: string; botId: string; botUsername: string; botName: string };
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
  testable: boolean;
};

export const PROVIDERS: Record<IntegrationProvider, ProviderMeta> = {
  OPENROUTER: { label: "OpenRouter", kind: "LLM_PROVIDER", secretLabel: "API-ключ", defaultBaseUrl: "https://openrouter.ai/api/v1", hasModel: true, testable: true },
  MAX: { label: "MAX", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://platform-api.max.ru", hasModel: false, testable: true },
  TELEGRAM: { label: "Telegram", kind: "MESSENGER", secretLabel: "Токен бота", defaultBaseUrl: "https://api.telegram.org", hasModel: false, testable: true },
  WEB: { label: "Web-виджет", kind: "MESSENGER", secretLabel: "", defaultBaseUrl: "", hasModel: false, testable: false },
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

// Публичный домен Hub для встраивания Web-виджета (SPEC-HUB-0003 §3).
// Подставляется в src сниппета: <hub>/chat-widget.js?data-channel=<code>.
const PUBLIC_HUB_URL = (import.meta.env.VITE_PUBLIC_HUB_URL ?? "").replace(/\/+$/, "");

export function webWidgetSnippet(channelCode: string): string {
  return `<script src="${PUBLIC_HUB_URL}/chat-widget.js" data-channel="${channelCode}" async></script>`;
}
