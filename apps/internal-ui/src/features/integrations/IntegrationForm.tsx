import { Modal } from "antd";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { fetchChannels, PROVIDERS, webWidgetSnippet, type ChannelOption, type Integration, type IntegrationProvider } from "./model";

const PROVIDER_OPTIONS: Array<[string, string]> = (Object.keys(PROVIDERS) as IntegrationProvider[]).map(
  (key) => [key, PROVIDERS[key].label],
);

export function IntegrationForm({ initial, onClose, onSaved }: { initial: Integration | null; onClose: () => void; onSaved: () => void }) {
  const isEdit = initial !== null;
  const [provider, setProvider] = useState<IntegrationProvider>(initial?.provider ?? "OPENROUTER");
  const [name, setName] = useState(initial?.name ?? "");
  const [secret, setSecret] = useState("");
  const [baseUrl, setBaseUrl] = useState(initial?.config.baseUrl ?? "");
  const [defaultModel, setDefaultModel] = useState(initial?.config.defaultModel ?? "");
  const [channelId, setChannelId] = useState(initial?.channel ? String(initial.channel.id) : "");
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const meta = PROVIDERS[provider];
  const isMessenger = meta.kind === "MESSENGER";
  const isWeb = provider === "WEB";
  const widgetChannel = channels.find((item) => String(item.id) === channelId) ?? null;
  const widgetSnippet = isWeb && widgetChannel ? webWidgetSnippet(widgetChannel.code) : "";

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
  const ready = name.trim().length > 0 && (isEdit || !meta.testable || secret.trim().length > 0);

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    const config = { baseUrl: baseUrl.trim(), defaultModel: defaultModel.trim() };
    const channel = isMessenger ? { channelId: channelId ? Number(channelId) : null } : {};
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
          <SelectField label="Тип" value={provider} onChange={(value) => setProvider(value as IntegrationProvider)} options={PROVIDER_OPTIONS} />
        )}
        <FormField label="Название" value={name} onChange={setName} placeholder="например, OpenRouter · основной" />
        {meta.testable && (
          <FormField
            label={meta.secretLabel}
            value={secret}
            onChange={setSecret}
            type="password"
            placeholder={isEdit ? "оставьте пустым, чтобы не менять" : ""}
          />
        )}
        <FormField label="Base URL" value={baseUrl} onChange={setBaseUrl} placeholder={meta.defaultBaseUrl || "—"} />
        {meta.hasModel && (
          <FormField label="Модель по умолчанию" value={defaultModel} onChange={setDefaultModel} placeholder="anthropic/claude-sonnet-4.6" />
        )}
        {isEdit && initial.config.botUsername && (
          <FormField label="Бот" value={`${initial.config.botName || initial.config.botUsername}${initial.config.botUsername ? ` · @${initial.config.botUsername}` : ""}${initial.config.botId ? ` · id ${initial.config.botId}` : ""}`} />
        )}
        {isMessenger && (
          <SelectField
            label="Канал обработки"
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
