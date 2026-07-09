import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../../api/client";
import { FormField, SelectField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { modelOptions } from "../create/model";
import type { AiAgentDetail } from "./model";

// Известные инструменты системы (services.py: operator-handoff). Хранятся как string[].
const TOOLS: Array<[string, string]> = [["operator-handoff", "Передача оператору"]];

// Фиксированный набор лимитов (release/model.ts limitLabel). Числовые поля.
const LIMIT_FIELDS: Array<[string, string]> = [
  ["dailyDialogs", "Диалогов в день"],
  ["maxMessagesPerDialog", "Макс. сообщений / диалог"],
  ["dailyBudgetRub", "Бюджет в день, ₽"],
  ["dailyCostMicros", "Бюджет в день, micros"],
];

function isNumber(value: string): boolean {
  return value === "" || /^\d+$/.test(value.trim());
}

export function AgentEditForm({ agent, onClose, onSaved }: { agent: AiAgentDetail; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(agent.name);
  const [model, setModel] = useState(agent.model);
  const [tools, setTools] = useState<string[]>(Array.isArray(agent.allowedTools) ? (agent.allowedTools as string[]) : []);
  const [limits, setLimits] = useState<Record<string, number>>({ ...(agent.limits as Record<string, number>) });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleTool(code: string) {
    setTools((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  function setLimit(key: string, value: string) {
    setLimits((current) => {
      const next = { ...current };
      const trimmed = value.trim();
      next[key] = trimmed === "" ? Number.NaN : Number(trimmed);
      return next;
    });
  }

  const limitsValid = Object.values(limits).every((value) => Number.isFinite(value));
  const ready = name.trim().length > 0 && limitsValid;

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    const cleanLimits: Record<string, number> = {};
    for (const [key, value] of Object.entries(limits)) {
      if (Number.isFinite(value)) cleanLimits[key] = value;
    }
    try {
      await api(`/api/v1/ai/agents/${agent.id}/update/`, {
        method: "PATCH",
        body: JSON.stringify({ name: name.trim(), model, allowedTools: tools, limits: cleanLimits }),
      });
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open title="Изменить агента" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <FormField label="Название" value={name} onChange={setName} placeholder="название агента" />
        <SelectField label="Модель" value={model} onChange={(value) => setModel(value)} options={modelOptions.map((option) => [option.value, option.label] as [string, string])} />
        <div className="ai-edit-tools">
          <span className="ai-edit-label">Инструменты</span>
          <div className="ai-edit-checks">
            {TOOLS.map(([code, label]) => (
              <label key={code} className="ai-edit-check">
                <input type="checkbox" checked={tools.includes(code)} onChange={() => toggleTool(code)} />
                {label}
              </label>
            ))}
          </div>
        </div>
        <div className="ai-edit-limits">
          <span className="ai-edit-label">Лимиты</span>
          <div className="ai-edit-limit-grid">
            {LIMIT_FIELDS.map(([key, label]) => (
              <label key={key} className="ai-edit-limit-field">
                <span>{label}</span>
                <input
                  type="text"
                  inputMode="numeric"
                  className={isNumber(String(limits[key] ?? "")) ? "" : "invalid"}
                  value={limits[key] === undefined || Number.isNaN(limits[key]) ? "" : String(limits[key])}
                  onChange={(event) => setLimit(key, event.target.value)}
                />
              </label>
            ))}
          </div>
        </div>
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!ready || submitting} onClick={submit}>{submitting ? "Сохранение…" : "Сохранить"}</Button>
        </div>
      </div>
    </Modal>
  );
}
