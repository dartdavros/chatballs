import { Modal } from "antd";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { EMAIL_CONFIG_DEFAULTS, EmailFields, emailConfigFromIntegration, emailConfigPayload } from "./EmailFields";
import {
  fetchChannels,
  formatAllowedOrigins,
  invalidAllowedOrigin,
  parseAllowedOrigins,
  PROVIDERS,
  webWidgetSnippet,
  type ChannelOption,
  type Integration,
  type IntegrationKind,
  type IntegrationProvider,
} from "./model";
import { t } from "../../i18n";

// Селектор «Тип» показывает только провайдеров рода активного таба (SPEC-CHATBALLS-0025 §2.2).
function providerOptions(kind: IntegrationKind): Array<[string, string]> {
  return (Object.keys(PROVIDERS) as IntegrationProvider[])
    .filter((key) => PROVIDERS[key].kind === kind)
    .map((key) => [key, PROVIDERS[key].label]);
}

export function IntegrationForm({ initial, kind, onClose, onSaved }: { initial: Integration | null; kind: IntegrationKind; onClose: () => void; onSaved: () => void }) {
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
  const [channels, setChannels] = useState<ChannelOption[]>([]);
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

  useEffect(() => {
    if (isMessenger) fetchChannels().then(setChannels).catch(() => setChannels([]));
  }, [isMessenger]);
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
    const channel = isMessenger ? { channelId: channelId && !isNotifier ? Number(channelId) : null } : {};
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

  return (
    <Modal open title={isEdit ? t("settings.edit_integration") : t("settings.new_integration")} onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        {isEdit ? (
          <FormField label={t("settings.type")} value={meta.label} />
        ) : (
          <SelectField label={t("settings.type")} value={provider} onChange={(value) => setProvider(value as IntegrationProvider)} options={options} />
        )}
        <FormField label={t("common.title")} value={name} onChange={setName} placeholder={isEmail ? t("settings.e_g_support_mailbox") : t("settings.e_g_openrouter_primary")} />
        {isEmail && <EmailFields value={emailConfig} onChange={setEmailConfig} />}
        {meta.testable && (
          <FormField
            label={meta.secretLabel}
            value={secret}
            onChange={setSecret}
            type="password"
            placeholder={isEdit ? t("settings.leave_empty_keep_unchanged") : ""}
          />
        )}
        {isEmail && !isEdit && (
          <div className="integration-form-hint">{t("settings.gmail_yandex_use_app_password")}</div>
        )}
        {isDemo && <div className="integration-form-hint">{t("settings.answers_from_agent_s_knowledge")}</div>}
        {!isEmail && !isWeb && !isDemo && <FormField label="Base URL" value={baseUrl} onChange={setBaseUrl} placeholder={meta.defaultBaseUrl || "—"} />}
        {isWeb && (
          <>
            <FormField
              label={t("settings.allowed_domains")}
              value={allowedOrigins}
              onChange={setAllowedOrigins}
              error={badOrigin && t("settings.unclear_domain", { domain: badOrigin })}
              placeholder={t("settings.example_com_example_com_comma")}
            />
            <div className="integration-form-hint">{t("settings.sites_where_widget_may_open")}</div>
          </>
        )}
        {!isWeb && !isEmail && !isDemo && (
          <>
            <FormField label={t("settings.proxy")} value={proxyUrl} onChange={setProxyUrl} placeholder={t("settings.http_host_port_or_socks5")} />
            <div className="integration-form-hint">{t("settings.proxy_password_never_returned_dots")}</div>
          </>
        )}
        {meta.hasModel && (
          <FormField label={t("settings.default_model")} value={defaultModel} onChange={setDefaultModel} placeholder={provider === "OPENROUTER" ? "anthropic/claude-sonnet-4.6" : ""} />
        )}
        {meta.hasModel && !isDemo && (
          <FormField label={t("settings.voice_transcription_model")} value={transcriptionModel} onChange={setTranscriptionModel} placeholder="whisper-1" />
        )}
        {isEdit && initial.config.botUsername && (
          <FormField label={t("settings.bot")} value={`${initial.config.botName || initial.config.botUsername}${initial.config.botUsername ? ` · @${initial.config.botUsername}` : ""}${initial.config.botId ? ` · id ${initial.config.botId}` : ""}`} />
        )}
        {isMessenger && !isWeb && !isEmail && (
          <label className="integration-notifier-toggle">
            <input type="checkbox" checked={isNotifier} onChange={(event) => setIsNotifier(event.target.checked)} />{t("settings.notification_bot_operators_service_bot")}</label>
        )}
        {isMessenger && !isNotifier && (
          <SelectField
            label={t("common.agent")}
            value={channelId}
            onChange={setChannelId}
            options={[["", t("settings.not_linked")], ...channels.map((c) => [String(c.id), c.name] as [string, string])]}
          />
        )}
        {widgetSnippet && (
          <div className="integration-snippet">
            <FormField label={t("settings.embed_snippet_site")} mono value={widgetSnippet} />
            <Button variant="secondary" icon={copied ? "check" : "copy"} iconSize={15} onClick={() => void copySnippet()}>
              {copied ? t("common.copied") : t("common.copy")}
            </Button>
          </div>
        )}
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="primary" disabled={!ready || submitting} onClick={submit}>{submitting ? t("ai.saving") : t("common.save")}</Button>
        </div>
      </div>
    </Modal>
  );
}
