import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../../api/client";
import { FormField, SelectField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { modelOptions } from "../create/model";
import type { AiAgentDetail } from "./model";

// Известные инструменты системы (services.py: operator-handoff). Хранятся как string[].
const TOOLS: Array<[string, string]> = [["operator-handoff", "Передача оператору"]];

// Дневной бюджет хранится в целых центах USD (dailyCostUsd); в поле вводим доллары.
function budgetFromCents(limits: Record<string, unknown>): string {
  const cents = limits?.dailyCostUsd;
  if (typeof cents !== "number" || cents <= 0) return "";
  return (cents / 100).toString();
}

// Допускаются неотрицательные доллары: до 2 знаков после запятой, разделитель «.» или «,».
function isBudget(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed === "") return true;
  return /^\d+([.,]\d{1,2})?$/.test(trimmed);
}

export function AgentEditForm({ agent, onClose, onSaved }: { agent: AiAgentDetail; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(agent.name);
  const [model, setModel] = useState(agent.model);
  const [tools, setTools] = useState<string[]>(Array.isArray(agent.allowedTools) ? (agent.allowedTools as string[]) : []);
  const [budget, setBudget] = useState(budgetFromCents(agent.limits as Record<string, unknown>));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleTool(code: string) {
    setTools((current) => (current.includes(code) ? current.filter((item) => item !== code) : [...current, code]));
  }

  const ready = name.trim().length > 0 && isBudget(budget);

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    const dollars = parseFloat(budget.trim().replace(",", "."));
    const limits: Record<string, number> = Number.isFinite(dollars) && dollars > 0 ? { dailyCostUsd: Math.round(dollars * 100) } : {};
    try {
      await api(`/api/v1/ai/agents/${agent.id}/update/`, {
        method: "PATCH",
        body: JSON.stringify({ name: name.trim(), model, allowedTools: tools, limits }),
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
            <label className="ai-edit-limit-field">
              <span>Бюджет в день, $</span>
              <input
                type="text"
                inputMode="decimal"
                className={isBudget(budget) ? "" : "invalid"}
                value={budget}
                placeholder="0.00"
                onChange={(event) => setBudget(event.target.value)}
              />
            </label>
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
