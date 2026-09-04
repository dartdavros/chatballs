import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import type { AiAgent } from "../model";
import { Button } from "../../../shared/ui-controls";
import { EmptyState, LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import {
  deleteAttachment,
  deleteKnowledgeItem,
  fetchKnowledgeItem,
  updateKnowledgeItem,
  uploadAttachment,
  type KnowledgeItem,
} from "./model";
import { KnowledgeAttachmentsCard } from "./KnowledgeAttachmentsCard";
import { KnowledgeDetailSidebar } from "./KnowledgeDetailSidebar";
import { KnowledgeEditorBreadcrumb } from "./KnowledgeEditorBreadcrumb";
import { KnowledgeEditorCard } from "./KnowledgeEditorCard";
import { knowledgeEditorError, knowledgeEditorRequest, knowledgeEditorState, type KnowledgeEditorState } from "./knowledgeEditorModel";
import { useKnowledgeCategories } from "./useKnowledgeCategories";

export function KnowledgeDetailPage({
  agents,
  canManage,
  knowledgeId,
  onLoaded,
  openAgent,
  setRoute,
}: {
  agents: AiAgent[];
  canManage: boolean;
  knowledgeId: number | null;
  onLoaded: (title: string | null) => void;
  openAgent: (agentId: number) => void;
  setRoute: (route: RouteKey) => void;
}) {
  const catalog = useKnowledgeCategories();
  const [item, setItem] = useState<KnowledgeItem | null>(null);
  const [state, setState] = useState<KnowledgeEditorState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const load = useCallback(async () => {
    if (!knowledgeId) return;
    setLoading(true);
    setLoadError(false);
    try {
      const { knowledge } = await fetchKnowledgeItem(knowledgeId);
      setItem(knowledge);
      setState(knowledgeEditorState(knowledge));
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [knowledgeId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    onLoaded(item?.title ?? null);
    return () => onLoaded(null);
  }, [item, onLoaded]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить знание");
    } finally {
      setBusy(false);
    }
  }

  if (loading || catalog.loading) return <div className="ai-page"><LoadingState /></div>;
  if (loadError || catalog.error || !item || !state) return <div className="ai-page"><EmptyState title="Не удалось загрузить знание" /></div>;

  async function save(activeItem: KnowledgeItem, editorState: KnowledgeEditorState) {
    const validationError = knowledgeEditorError(editorState);
    if (validationError) { setError(validationError); return; }
    await run(() => updateKnowledgeItem(activeItem.id, knowledgeEditorRequest(editorState)));
  }

  return (
    <div className="ai-page knowledge-editor-page">
      <KnowledgeEditorBreadcrumb categories={catalog.categories} categoryId={state.categoryId} title={state.title} onBack={() => setRoute("aiKnowledge")} />
      <div className="knowledge-editor-grid">
        <div className="knowledge-editor-main">
          <KnowledgeEditorCard
            busy={busy}
            categories={catalog.categories}
            editable={canManage}
            error={error}
            item={item}
            state={state}
            onChange={setState}
            onDelete={() => setDeleteOpen(true)}
            onSave={() => void save(item, state)}
            onToggleEnabled={() => void run(() => updateKnowledgeItem(item.id, { isEnabled: !state.isEnabled }))}
          />
          <KnowledgeAttachmentsCard
            attachments={item.attachments}
            busy={busy || !canManage}
            onAdd={(files) => void run(async () => { for (const file of files) await uploadAttachment(item.id, file); })}
            onDelete={(attachment) => { if ("id" in attachment) void run(() => deleteAttachment(item.id, attachment.id)); }}
          />
        </div>
        <KnowledgeDetailSidebar agents={agents} item={item} openAgent={openAgent} />
      </div>
      {deleteOpen && (
        <Modal open title="Удалить знание?" onCancel={() => setDeleteOpen(false)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>Знание «{item.title}» и его вложения будут удалены. У агентов, использующих это знание, оно исчезнет из выбора.</p>
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setDeleteOpen(false)}>Отмена</Button>
              <Button variant="primary" disabled={busy} onClick={() => { setBusy(true); void deleteKnowledgeItem(item.id).then(() => setRoute("aiKnowledge")).catch(() => setBusy(false)); }}>Удалить</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
