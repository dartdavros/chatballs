import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../api/client";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { PROVIDERS, type Integration, type IntegrationProvider } from "./model";

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
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meta = PROVIDERS[provider];
  const ready = name.trim().length > 0 && (isEdit || !meta.testable || secret.trim().length > 0);

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    const config = { baseUrl: baseUrl.trim(), defaultModel: defaultModel.trim() };
    try {
      if (isEdit) {
        await api(`/api/v1/integrations/${initial.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ name, config, ...(secret.trim() ? { secret } : {}) }),
        });
      } else {
        await api("/api/v1/integrations/", {
          method: "POST",
          body: JSON.stringify({ provider, name, secret, config }),
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
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!ready || submitting} onClick={submit}>{submitting ? "Сохранение…" : "Сохранить"}</Button>
        </div>
      </div>
    </Modal>
  );
}
