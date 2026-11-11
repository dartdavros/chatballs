import { Modal } from "antd";
import { helpArticleUrl } from "../../shared/help";
import { Icon } from "../../shared/icons";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { EmailFields } from "./EmailFields";
import type { Integration, IntegrationKind, IntegrationProvider } from "./model";
import { t } from "../../i18n";
import { ConnectionRouteFields } from "./ConnectionRouteFields";
import { useIntegrationForm } from "./useIntegrationForm";

export function IntegrationForm({ initial, kind, allowedProviders, title, onClose, onSaved, onSpeechKit }: {
  initial: Integration | null; kind: IntegrationKind; allowedProviders?: readonly IntegrationProvider[]; title?: string;
  onClose: () => void; onSaved: () => void; onSpeechKit?: () => void;
}) {
  const { isEdit, options, provider, setProvider, name, setName, secret, setSecret, baseUrl, setBaseUrl, defaultModel, setDefaultModel, transcriptionModel, setTranscriptionModel, proxyUrl, setProxyUrl, allowedOrigins, setAllowedOrigins, emailConfig, setEmailConfig, channelId, setChannelId, groupId, setGroupId, isNotifier, setIsNotifier, submitting, error, copied, meta, isMessenger, isWeb, isEmail, isDemo, widgetSnippet, copySnippet, badOrigin, ready, submit } = useIntegrationForm({ initial, kind, allowedProviders, onSaved });

  return (
    <Modal open title={title ?? (isEdit ? t("settings.edit_integration") : t("settings.new_integration"))} onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        {isEdit || options.length === 1 ? (
          <FormField label={t("settings.type")} value={meta.label} />
        ) : (
          <SelectField label={t("settings.type")} value={provider} onChange={(value) => { if (value === "YANDEX_SPEECHKIT" && onSpeechKit) onSpeechKit(); else setProvider(value as IntegrationProvider); }} options={options} />
        )}
        {meta.helpSlug && (
          <a className="link is-muted has-icon integration-form-help" href={helpArticleUrl(meta.helpSlug)} target="_blank" rel="noopener noreferrer">
            {t("settings.how_to_connect")}
            <Icon name="external" size={13} strokeWidth={2.2} />
          </a>
        )}
        <FormField label={t("common.title")} value={name} onChange={setName}
          placeholder={isEmail ? t("settings.e_g_support_mailbox") : isMessenger ? "" : t("settings.e_g_openrouter_primary")} />
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
        {initial && initial.config.botUsername && (
          <FormField label={t("settings.bot")} value={`${initial.config.botName || initial.config.botUsername}${initial.config.botUsername ? ` · @${initial.config.botUsername}` : ""}${initial.config.botId ? ` · id ${initial.config.botId}` : ""}`} />
        )}
        {isMessenger && !isWeb && !isEmail && (
          <label className="integration-notifier-toggle">
            <input type="checkbox" checked={isNotifier} onChange={(event) => setIsNotifier(event.target.checked)} />{t("settings.notification_bot_operators_service_bot")}</label>
        )}
        {isMessenger && !isNotifier && (
          <ConnectionRouteFields initial={initial} channelId={channelId} onChannel={setChannelId} groupId={groupId} onGroup={setGroupId} />
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
