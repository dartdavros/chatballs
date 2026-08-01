import { useState } from "react";

import { Icon } from "../../../shared/icons";
import {
  AgentLinkDialog,
  type AgentLinkAction,
  type AgentLinkOption,
  type AgentLinkOutcome,
} from "../../../shared/content-library/AgentLinkDialog";
import { BulkSelectionBar } from "../../../shared/content-library/BulkSelectionBar";
import {
  bulkMoveKnowledge,
  bulkReplaceKnowledgeVisibility,
  isKnowledgeScopeConflict,
  linkKnowledgeToAgent,
} from "./model";
import { KnowledgeBulkDialog, type KnowledgeBulkMode } from "./KnowledgeBulkDialog";
import { KnowledgeScopeConflictModal } from "./KnowledgeScopeConflictModal";
import type { KnowledgeCategory, KnowledgeDepartmentReference, KnowledgeScopeConflict, KnowledgeVisibility } from "./types";

const KNOWLEDGE_FORMS: [string, string, string] = ["знание", "знания", "знаний"];

export function KnowledgeBulkActions({
  agents,
  canLinkAgents,
  categories,
  departments,
  selectedIds,
  onClear,
  onComplete,
  openAgent,
}: {
  agents: AgentLinkOption[];
  canLinkAgents: boolean;
  categories: KnowledgeCategory[];
  departments: KnowledgeDepartmentReference[];
  selectedIds: Set<number>;
  onClear: () => void;
  onComplete: () => Promise<void>;
  openAgent: (agentId: number) => void;
}) {
  const [mode, setMode] = useState<KnowledgeBulkMode | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [outcome, setOutcome] = useState<AgentLinkOutcome | null>(null);
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [visibility, setVisibility] = useState<KnowledgeVisibility>("ORGANIZATION");
  const [departmentIds, setDepartmentIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<KnowledgeScopeConflict[]>([]);

  function open(nextMode: KnowledgeBulkMode) {
    setMode(nextMode);
    setError(null);
    setCategoryId(null);
    setVisibility(nextMode === "departments" ? "DEPARTMENTS" : "ORGANIZATION");
    setDepartmentIds([]);
  }

  function openAgentDialog() {
    setAgentOpen(true);
    setOutcome(null);
    setError(null);
  }

  async function submit() {
    if (!mode) return;
    if (mode === "move" && categoryId === null) { setError("Выберите категорию"); return; }
    if (mode !== "move" && visibility === "DEPARTMENTS" && departmentIds.length === 0) { setError("Выберите хотя бы один отдел"); return; }
    setBusy(true);
    setError(null);
    try {
      const knowledgeIds = [...selectedIds];
      if (mode === "move") await bulkMoveKnowledge({ knowledgeIds, categoryId: categoryId as number });
      else await bulkReplaceKnowledgeVisibility({ knowledgeIds, visibility, departmentIds: visibility === "DEPARTMENTS" ? departmentIds : [] });
      setMode(null);
      await onComplete();
    } catch (caught) {
      if (isKnowledgeScopeConflict(caught)) { setConflicts(caught.payload.conflicts); setMode(null); }
      else setError(caught instanceof Error ? caught.message : "Не удалось применить операцию");
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
        <button type="button" onClick={() => open("move")}><Icon name="folder" size={15} />Переместить в категорию</button>
        <button type="button" onClick={() => open("visibility")}><Icon name="eye" size={15} />Изменить доступность</button>
        <button type="button" onClick={() => open("departments")}><Icon name="building" size={15} />Заменить отделы</button>
        {canLinkAgents && <button type="button" onClick={openAgentDialog}><Icon name="robot" size={15} />Прикрепить к агенту</button>}
      </BulkSelectionBar>
      {mode && (
        <KnowledgeBulkDialog
          busy={busy}
          categories={categories}
          categoryId={categoryId}
          departmentIds={departmentIds}
          departments={departments}
          error={error}
          mode={mode}
          visibility={visibility}
          onCancel={() => setMode(null)}
          onCategoryChange={setCategoryId}
          onDepartmentChange={setDepartmentIds}
          onSubmit={() => void submit()}
          onVisibilityChange={(value) => { setVisibility(value); if (value === "ORGANIZATION") setDepartmentIds([]); }}
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
      {conflicts.length > 0 && <KnowledgeScopeConflictModal conflicts={conflicts} onClose={() => setConflicts([])} openAgent={openAgent} />}
    </>
  );
}
