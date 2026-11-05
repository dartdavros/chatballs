import { useState } from "react";
import { api } from "../../api/client";
import { t } from "../../i18n";
import { EMAIL_CONFIG_DEFAULTS, emailConfigFromIntegration, emailConfigPayload } from "./EmailFields";
import { connectionGroupSettings, formatAllowedOrigins, invalidAllowedOrigin, parseAllowedOrigins, PROVIDERS, webWidgetSnippet,
  type Integration, type IntegrationKind, type IntegrationProvider } from "./model";

// Селектор «Тип» показывает только провайдеров рода активного таба (SPEC-CHATBALLS-0025 §2.2).
function providerOptions(kind: IntegrationKind): Array<[string, string]> {
  return (Object.keys(PROVIDERS) as IntegrationProvider[])
    .filter((key) => PROVIDERS[key].kind === kind || (kind === "LLM_PROVIDER" && PROVIDERS[key].kind === "SPEECH_PROVIDER"))
    .sort((left, right) => Number(left === "YANDEX_SPEECHKIT") - Number(right === "YANDEX_SPEECHKIT"))
    .map((key) => [key, PROVIDERS[key].label]);
}

export function useIntegrationForm({ initial, kind, onSaved }: { initial: Integration | null; kind: IntegrationKind; onSaved: () => void }) {
  const isEdit = initial !== null;
  const options = providerOptions(kind);
  const [provider, setProvider] = useState<IntegrationProvider>(initial?.provider ?? (options[0][0] as IntegrationProvider));
  const [name, setName] = useState(initial?.name ?? "");
  const [secret, setSecret] = useState("");
  const [baseUrl, setBaseUrl] = useState(initial?.config.baseUrl ?? "");
  const [defaultModel, setDefaultModel] = useState(initial?.config.defaultModel ?? "");
  const [transcriptionModel, setTranscriptionModel] = useState(initial?.config.transcriptionModel ?? "");
  const [proxyUrl, setProxyUrl] = useState(initial?.config.proxyUrl ?? "");
  const [allowedOrigins, setAllowedOrigins] = useState(formatAllowedOrigins(initial?.config.allowedOrigins ?? []));
  const [emailConfig, setEmailConfig] = useState(initial ? emailConfigFromIntegration(initial.config) : EMAIL_CONFIG_DEFAULTS);
  const [channelId, setChannelId] = useState(initial?.channel ? String(initial.channel.id) : "");
  const [isNotifier, setIsNotifier] = useState(initial?.config.purpose === "notifications");
  const [groupId, setGroupId] = useState(initial?.channel?.groupId ? String(initial.channel.groupId) : "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const meta = PROVIDERS[provider];
  const isMessenger = meta.kind === "MESSENGER";
  const isWeb = provider === "WEB";
  const isEmail = provider === "EMAIL";
  const isDemo = provider === "DEMO";
  const widgetSnippet = isWeb && initial?.webChatWidget
    ? webWidgetSnippet(initial.webChatWidget.publicKey)
    : "";

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(widgetSnippet);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  const customReady = provider !== "CUSTOM" || (baseUrl.trim().length > 0 && defaultModel.trim().length > 0);
  const emailReady = !isEmail || Boolean(emailConfig.email.trim() && emailConfig.imapHost.trim() && emailConfig.smtpHost.trim());
  // Без доменов виджет сохранится, но на сайте покажет «Чат временно недоступен»:
  // origin_allowed на пустом списке запрещает всё. Поэтому поле обязательное.
  const originList = parseAllowedOrigins(allowedOrigins);
  const badOrigin = isWeb ? invalidAllowedOrigin(originList) : undefined;
  const webReady = !isWeb || (originList.length > 0 && !badOrigin);
  const ready = name.trim().length > 0 && customReady && emailReady && webReady && (isEdit || !meta.testable || secret.trim().length > 0);

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    const config = isEmail
      ? emailConfigPayload(emailConfig)
      : isWeb
        ? {
            allowedOrigins: originList,
            title: initial?.config.title ?? "",
            accent: initial?.config.accent ?? "",
            greeting: initial?.config.greeting ?? "",
            quickReplies: initial?.config.quickReplies ?? [],
            consentText: initial?.config.consentText ?? "",
            consentVersion: initial?.config.consentVersion ?? "",
          }
        : { baseUrl: baseUrl.trim(), defaultModel: defaultModel.trim(), transcriptionModel: transcriptionModel.trim(), proxyUrl: proxyUrl.trim(), purpose: isNotifier ? "notifications" : "" };
    // Сервисный бот уведомлений не привязывается к каналу продаж.
    const channel = isMessenger ? { channelId: channelId && !isNotifier ? Number(channelId) : null, ...(!isNotifier ? connectionGroupSettings(initial, channelId, groupId) : {}) } : {};
    try {
      if (isEdit) {
        await api(`/api/v1/integrations/${initial.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ name, config, ...channel, ...(secret.trim() ? { secret } : {}) }),
        });
      } else {
        await api("/api/v1/integrations/", {
          method: "POST",
          body: JSON.stringify({ provider, name, secret, config, ...channel }),
        });
      }
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.could_not_save"));
    } finally {
      setSubmitting(false);
    }
  }

  return { isEdit, options, provider, setProvider, name, setName, secret, setSecret, baseUrl, setBaseUrl, defaultModel, setDefaultModel, transcriptionModel, setTranscriptionModel, proxyUrl, setProxyUrl, allowedOrigins, setAllowedOrigins, emailConfig, setEmailConfig, channelId, setChannelId, groupId, setGroupId, isNotifier, setIsNotifier, submitting, error, copied, meta, isMessenger, isWeb, isEmail, isDemo, widgetSnippet, copySnippet, badOrigin, ready, submit };
}
