import { useState } from "react";

import { api } from "../../../api/client";
import { Button } from "../../../shared/ui-controls";
import type { AiAgentDetail } from "./model";

const FIELDS: Array<{ key: "persona" | "tone" | "instructions"; title: string; hint: string }> = [
  { key: "persona", title: "Персонализация", hint: "Кто он и что он: имя, роль, продукт, рамки ответственности." },
  { key: "tone", title: "Тон общения", hint: "Как он должен говорить: стиль, формат, язык." },
  { key: "instructions", title: "Инструкции", hint: "Правила работы: что делать, чего не делать, когда передавать оператору." },
];

export function AiAgentInstructionsTab({ agent, onChanged }: { agent: AiAgentDetail; onChanged: () => void }) {
  const [values, setValues] = useState({ persona: agent.persona, tone: agent.tone, instructions: agent.instructions });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty = values.persona !== agent.persona || values.tone !== agent.tone || values.instructions !== agent.instructions;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/ai/agents/${agent.id}/update/`, { method: "PATCH", body: JSON.stringify(values) });
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-instructions">
      {FIELDS.map((field, index) => (
        <section className="ai-card ai-doc-card" key={field.key}>
          <div className="ai-instruction-head">
            <span className="ai-instruction-index">{index + 1}</span>
            <h3>{field.title}</h3>
            <small>{field.hint}</small>
          </div>
          <textarea
            className="ai-doc-textarea"
            rows={field.key === "instructions" ? 10 : 5}
            value={values[field.key]}
            onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
          />
        </section>
      ))}
      {error && <div className="ai-doc-error">{error}</div>}
      <div className="ai-doc-actions">
        <Button variant="primary" icon="save" disabled={!dirty || busy} onClick={save}>{busy ? "Сохранение…" : "Сохранить инструкции"}</Button>
        <span className="ai-doc-updated">Изменения применяются к следующему ответу агента сразу после сохранения.</span>
      </div>
    </div>
  );
}
