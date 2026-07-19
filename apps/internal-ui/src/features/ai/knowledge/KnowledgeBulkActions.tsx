import { useState } from "react";

import { Icon } from "../../../shared/icons";
import {
  bulkMoveKnowledge,
  bulkReplaceKnowledgeVisibility,
  isKnowledgeScopeConflict,
} from "./model";
import { KnowledgeBulkDialog, type KnowledgeBulkMode } from "./KnowledgeBulkDialog";
import { KnowledgeScopeConflictModal } from "./KnowledgeScopeConflictModal";
import type { KnowledgeCategory, KnowledgeDepartmentReference, KnowledgeScopeConflict, KnowledgeVisibility } from "./types";

function selectedKnowledgeLabel(count: number): string {
  const remainder100 = count % 100;
  const remainder10 = count % 10;
  if (remainder100 >= 11 && remainder100 <= 14) return "знаний";
  if (remainder10 === 1) return "знание";
  if (remainder10 >= 2 && remainder10 <= 4) return "знания";
  return "знаний";
}

export function KnowledgeBulkActions({
  categories,
  departments,
  selectedIds,
  onClear,
  onComplete,
  openAgent,
}: {
  categories: KnowledgeCategory[];
  departments: KnowledgeDepartmentReference[];
  selectedIds: Set<number>;
  onClear: () => void;
  onComplete: () => Promise<void>;
  openAgent: (agentId: number) => void;
}) {
  const [mode, setMode] = useState<KnowledgeBulkMode | null>(null);
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

  return (
    <>
      <div className="knowledge-bulk-bar">
        <span className="knowledge-bulk-check"><Icon name="check" size={12} /></span>
        <strong>Выбрано {selectedIds.size} {selectedKnowledgeLabel(selectedIds.size)}</strong>
        <i />
        <button type="button" onClick={() => open("move")}><Icon name="folder" size={15} />Переместить в категорию</button>
        <button type="button" onClick={() => open("visibility")}><Icon name="eye" size={15} />Изменить доступность</button>
        <button type="button" onClick={() => open("departments")}><Icon name="building" size={15} />Заменить отделы</button>
        <span />
        <button className="knowledge-bulk-clear" type="button" onClick={onClear}>Снять выбор</button>
      </div>
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
      {conflicts.length > 0 && <KnowledgeScopeConflictModal conflicts={conflicts} onClose={() => setConflicts([])} openAgent={openAgent} />}
    </>
  );
}
