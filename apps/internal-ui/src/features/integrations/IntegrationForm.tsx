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

// Селектор «Тип» показывает только провайдеров рода активного таба (SPEC-HUB-0025 §2.2).
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
        : { baseUrl: baseUrl.trim(), defaultModel: defaultModel.trim(), proxyUrl: proxyUrl.trim(), purpose: isNotifier ? "notifications" : "" };
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
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open title={isEdit ? "Изменить интеграцию" : "Новая интеграция"} onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        {isEdit ? (
          <FormField label="Тип" value={meta.label} />
        ) : (
          <SelectField label="Тип" value={provider} onChange={(value) => setProvider(value as IntegrationProvider)} options={options} />
        )}
        <FormField label="Название" value={name} onChange={setName} placeholder={isEmail ? "например, Почта поддержки" : "например, OpenRouter · основной"} />
        {isEmail && <EmailFields value={emailConfig} onChange={setEmailConfig} />}
        {meta.testable && (
          <FormField
            label={meta.secretLabel}
            value={secret}
            onChange={setSecret}
            type="password"
            placeholder={isEdit ? "оставьте пустым, чтобы не менять" : ""}
          />
        )}
        {isEmail && !isEdit && (
          <div className="integration-form-hint">Для Gmail и Яндекс используйте пароль приложения, не основной пароль аккаунта</div>
        )}
        {!isEmail && !isWeb && <FormField label="Base URL" value={baseUrl} onChange={setBaseUrl} placeholder={meta.defaultBaseUrl || "—"} />}
        {isWeb && (
          <>
            <FormField
              label="Разрешённые домены"
              value={allowedOrigins}
              onChange={setAllowedOrigins}
              error={badOrigin && `Непонятный домен: ${badOrigin}`}
              placeholder="example.com, *.example.com — через запятую"
            />
            <div className="integration-form-hint">Сайты, на которых виджету разрешено открываться: домен, поддомены через «*.» или полный origin с портом. На остальных чат ответит «Чат временно недоступен»</div>
          </>
        )}
        {!isWeb && !isEmail && (
          <FormField label="Прокси" value={proxyUrl} onChange={setProxyUrl} placeholder="http://host:port или socks5://user:pass@host:port — пусто, если без прокси" />
        )}
        {meta.hasModel && (
          <FormField label="Модель по умолчанию" value={defaultModel} onChange={setDefaultModel} placeholder={provider === "OPENROUTER" ? "anthropic/claude-sonnet-4.6" : ""} />
        )}
        {isEdit && initial.config.botUsername && (
          <FormField label="Бот" value={`${initial.config.botName || initial.config.botUsername}${initial.config.botUsername ? ` · @${initial.config.botUsername}` : ""}${initial.config.botId ? ` · id ${initial.config.botId}` : ""}`} />
        )}
        {isMessenger && !isWeb && !isEmail && (
          <label className="integration-notifier-toggle">
            <input type="checkbox" checked={isNotifier} onChange={(event) => setIsNotifier(event.target.checked)} />
            Бот уведомлений для сотрудников (сервисный, клиентам не отвечает; привязка в профиле)
          </label>
        )}
        {isMessenger && !isNotifier && (
          <SelectField
            label="Агент"
            value={channelId}
            onChange={setChannelId}
            options={[["", "— не привязан —"], ...channels.map((c) => [String(c.id), c.name] as [string, string])]}
          />
        )}
        {widgetSnippet && (
          <div className="integration-snippet">
            <FormField label="Код вставки на сайт" mono value={widgetSnippet} />
            <Button variant="secondary" icon={copied ? "check" : "copy"} iconSize={15} onClick={() => void copySnippet()}>
              {copied ? "Скопировано" : "Копировать"}
            </Button>
          </div>
        )}
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!ready || submitting} onClick={submit}>{submitting ? "Сохранение…" : "Сохранить"}</Button>
        </div>
      </div>
    </Modal>
  );
}
