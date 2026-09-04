import { useState } from "react";

import { Icon } from "../../../shared/icons";
import {
  AgentLinkDialog,
  type AgentLinkAction,
  type AgentLinkOption,
  type AgentLinkOutcome,
} from "../../../shared/content-library/AgentLinkDialog";
import { BulkSelectionBar } from "../../../shared/content-library/BulkSelectionBar";
import { bulkMoveKnowledge, linkKnowledgeToAgent } from "./model";
import { KnowledgeBulkDialog } from "./KnowledgeBulkDialog";
import type { KnowledgeCategory } from "./types";

const KNOWLEDGE_FORMS: [string, string, string] = ["знание", "знания", "знаний"];

export function KnowledgeBulkActions({
  agents,
  canLinkAgents,
  categories,
  selectedIds,
  onClear,
  onComplete,
}: {
  agents: AgentLinkOption[];
  canLinkAgents: boolean;
  categories: KnowledgeCategory[];
  selectedIds: Set<number>;
  onClear: () => void;
  onComplete: () => Promise<void>;
}) {
  const [moveOpen, setMoveOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const [outcome, setOutcome] = useState<AgentLinkOutcome | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openMoveDialog() {
    setMoveOpen(true);
    setError(null);
    setCategoryId(null);
  }

  function openAgentDialog() {
    setAgentOpen(true);
    setOutcome(null);
    setError(null);
  }

  async function submit() {
    if (categoryId === null) { setError("Выберите категорию"); return; }
    setBusy(true);
    setError(null);
    try {
      await bulkMoveKnowledge({ knowledgeIds: [...selectedIds], categoryId });
      setMoveOpen(false);
      await onComplete();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось применить операцию");
    } finally {
      setBusy(false);
    }
  }

  async function submitAgentLink(agentId: number, action: AgentLinkAction) {
    setBusy(true);
    setError(null);
    try {
      const result = await linkKnowledgeToAgent({ agentId, action, knowledgeIds: [...selectedIds] });
      // onComplete снимает выбор и размонтирует панель вместе с диалогом,
      // поэтому список перечитывается только после закрытия отчёта.
      setOutcome({ action, changed: result.changed, skipped: result.skippedIds.length });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось изменить знания агента");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <BulkSelectionBar count={selectedIds.size} forms={KNOWLEDGE_FORMS} onClear={onClear}>
        <button type="button" onClick={openMoveDialog}><Icon name="folder" size={15} />Переместить в категорию</button>
        {canLinkAgents && <button type="button" onClick={openAgentDialog}><Icon name="robot" size={15} />Прикрепить к агенту</button>}
      </BulkSelectionBar>
      {moveOpen && (
        <KnowledgeBulkDialog
          busy={busy}
          categories={categories}
          categoryId={categoryId}
          error={error}
          onCancel={() => setMoveOpen(false)}
          onCategoryChange={setCategoryId}
          onSubmit={() => void submit()}
        />
      )}
      {agentOpen && (
        <AgentLinkDialog
          agents={agents}
          busy={busy}
          error={error}
          forms={KNOWLEDGE_FORMS}
          outcome={outcome}
          title="Знания агента"
          onCancel={() => { setAgentOpen(false); if (outcome) void onComplete(); }}
          onSubmit={(agentId, action) => void submitAgentLink(agentId, action)}
        />
      )}
    </>
  );
}
