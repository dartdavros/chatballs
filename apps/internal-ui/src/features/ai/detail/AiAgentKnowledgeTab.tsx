import { useState } from "react";

import { api } from "../../../api/client";
import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { KnowledgeItem } from "../knowledge/model";
import type { AiAgentDetail } from "./model";

export function AiAgentKnowledgeTab({ agent, library, openKnowledge, onChanged }: { agent: AiAgentDetail; library: KnowledgeItem[]; openKnowledge: (knowledgeId: number) => void; onChanged: () => void }) {
  const [selected, setSelected] = useState<number[]>(agent.knowledge.map((item) => item.id));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = agent.knowledge.map((item) => item.id).sort().join(",");
  const dirty = [...selected].sort().join(",") !== initial;

  function toggle(id: number) {
    setSelected((ids) => (ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]));
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/ai/agents/${agent.id}/update/`, { method: "PATCH", body: JSON.stringify({ knowledgeIds: selected }) });
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-instructions">
      <div className="ai-knowledge-headline">Выбор знаний · {agent.channel.name} · выбрано {selected.length} из {library.length}</div>
      {library.length === 0 && <EmptyState title="В библиотеке пока нет знаний — создайте их в разделе «Знания»" />}
      {library.length > 0 && (
        <section className="ai-card">
          <ul className="agent-knowledge-list">
            {library.map((item) => {
              const checked = selected.includes(item.id);
              return (
                <li key={item.id} className={checked ? "is-selected" : ""}>
                  <label>
                    <input type="checkbox" checked={checked} onChange={() => toggle(item.id)} />
                    <span className="agent-knowledge-text">
                      <strong>{item.title}</strong>
                      <small>{item.description || "—"}</small>
                    </span>
                  </label>
                  {!item.isEnabled && <span className="ai-doc-chip off">Выключено</span>}
                  {item.attachments.length > 0 && <span className="ai-doc-chip plain"><Icon name="paperclip" size={12} /> {item.attachments.length}</span>}
                  <button type="button" className="row-menu-button" aria-label="Открыть знание" onClick={() => openKnowledge(item.id)}><Icon name="external" size={15} /></button>
                </li>
              );
            })}
          </ul>
          {error && <div className="ai-doc-error">{error}</div>}
          <div className="ai-doc-actions">
            <Button variant="primary" icon="save" disabled={!dirty || busy} onClick={save}>{busy ? "Сохранение…" : "Сохранить выбор"}</Button>
            <span className="ai-doc-updated">Агент использует только выбранные и включённые знания.</span>
          </div>
        </section>
      )}
    </div>
  );
}
