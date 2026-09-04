import { useEffect, useState } from "react";

import type { RouteKey } from "../../../types";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { createKnowledgeItem, deleteKnowledgeItem, uploadAttachment } from "./model";
import { KnowledgeAttachmentsCard } from "./KnowledgeAttachmentsCard";
import { KnowledgeEditorBreadcrumb } from "./KnowledgeEditorBreadcrumb";
import { KnowledgeEditorCard } from "./KnowledgeEditorCard";
import { emptyKnowledgeEditorState, knowledgeEditorError, knowledgeEditorRequest } from "./knowledgeEditorModel";
import { useKnowledgeCategories } from "./useKnowledgeCategories";

export function KnowledgeCreatePage({
  openKnowledge,
  setRoute,
}: {
  openKnowledge: (knowledgeId: number) => void;
  setRoute: (route: RouteKey) => void;
}) {
  const catalog = useKnowledgeCategories();
  const [state, setState] = useState(() => emptyKnowledgeEditorState());
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (state.categoryId !== null || catalog.categories.length === 0) return;
    const defaultCategory = catalog.categories.find((category) => category.isSystem) ?? catalog.categories[0];
    setState((current) => ({ ...current, categoryId: defaultCategory.id }));
  }, [catalog.categories, state.categoryId]);

  async function create() {
    const validationError = knowledgeEditorError(state);
    if (validationError) { setError(validationError); return; }
    setBusy(true);
    setError(null);
    let createdId: number | null = null;
    try {
      const { knowledge } = await createKnowledgeItem(knowledgeEditorRequest(state));
      createdId = knowledge.id;
      for (const file of files) await uploadAttachment(knowledge.id, file);
      openKnowledge(knowledge.id);
    } catch (caught) {
      if (createdId !== null) await deleteKnowledgeItem(createdId).catch(() => undefined);
      setError(caught instanceof Error ? caught.message : "Не удалось создать знание");
    } finally {
      setBusy(false);
    }
  }

  if (catalog.loading) return <div className="ai-page"><LoadingState /></div>;
  if (catalog.error) return <div className="ai-page"><EmptyState title="Не удалось загрузить категории" /></div>;

  return (
    <div className="ai-page knowledge-editor-page">
      <KnowledgeEditorBreadcrumb categories={catalog.categories} categoryId={state.categoryId} title={state.title} onBack={() => setRoute("aiKnowledge")} />
      <div className="knowledge-editor-grid create">
        <div className="knowledge-editor-main">
          <KnowledgeEditorCard
            busy={busy}
            categories={catalog.categories}
            editable
            error={error}
            item={null}
            state={state}
            onChange={setState}
            onSave={() => void create()}
          />
          <KnowledgeAttachmentsCard
            attachments={files}
            busy={busy}
            onAdd={(nextFiles) => setFiles((current) => [...current, ...nextFiles])}
            onDelete={(attachment) => setFiles((current) => current.filter((file) => file !== attachment))}
          />
        </div>
      </div>
    </div>
  );
}
