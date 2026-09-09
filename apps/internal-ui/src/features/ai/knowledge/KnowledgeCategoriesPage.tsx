import { useMemo, useState, type DragEvent } from "react";

import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import {
  buildCategoryTree,
  planCategoryDrop,
  type CategoryDropPosition,
  type ManagedContentCategoryNode,
} from "../../../shared/content-library/categoryManagementModel";
import type { RouteKey } from "../../../types";
import {
  createKnowledgeCategory,
  deleteKnowledgeCategory,
  updateKnowledgeCategory,
} from "./model";
import { useKnowledgeCategories } from "./useKnowledgeCategories";
import { t, tn } from "../../../i18n";

// Категории знаний (дизайн-базлайн v2, кадр KB7): отдельный экран, а не
// модалка — дерево строками с перетаскиванием, инлайн-переименованием и
// безопасным удалением. Правила и причина запрета — карточками справа.

type Row = { node: ManagedContentCategoryNode; depth: number };

function flatten(nodes: ManagedContentCategoryNode[], depth = 0): Row[] {
  return nodes.flatMap((node) => [{ node, depth }, ...flatten(node.children, depth + 1)]);
}

/** «18 знаний · 2 вложенные» — подпись строки категории. */
function countLabel(node: ManagedContentCategoryNode): string {
  if (node.count === 0 && node.children.length === 0) return t("ai.empty");
  const knowledge = tn("plural.knowledge", node.count);
  if (node.children.length === 0) return knowledge;
  return `${knowledge} · ${tn("plural.nested", node.children.length)}`;
}

/** Почему нельзя удалить: системная, есть вложенные, есть материалы. */
function deleteBlock(node: ManagedContentCategoryNode): string | null {
  if (node.isSystem) return t("ai.system_category");
  if (node.children.length > 0) return t("ai.has_nested_categories");
  if (node.count > 0) return t("ai.category_not_empty");
  return null;
}

function dropPosition(event: DragEvent<HTMLDivElement>, isSystem: boolean): CategoryDropPosition {
  const bounds = event.currentTarget.getBoundingClientRect();
  const offset = (event.clientY - bounds.top) / bounds.height;
  if (offset < 0.3) return "before";
  if (offset > 0.7 || isSystem) return "after";
  return "inside";
}

export function KnowledgeCategoriesPage({
  canManage,
  setRoute,
}: {
  canManage: boolean;
  setRoute: (route: RouteKey) => void;
}) {
  const catalog = useKnowledgeCategories();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [createParentId, setCreateParentId] = useState<number | null | undefined>();
  const [draftName, setDraftName] = useState("");
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [blocked, setBlocked] = useState<{ name: string; reason: string } | null>(null);
  const [deleting, setDeleting] = useState<ManagedContentCategoryNode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const managed = useMemo(() => catalog.categories.map((category) => ({
    id: category.id,
    name: category.name,
    parentId: category.parentId,
    sortOrder: category.sortOrder,
    count: category.knowledgeCount ?? 0,
    isSystem: category.isSystem,
  })), [catalog.categories]);
  const rows = useMemo(() => flatten(buildCategoryTree(managed)), [managed]);

  function cancel() {
    setEditingId(null);
    setCreateParentId(undefined);
    setDraftName("");
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      cancel();
      await catalog.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("shared.could_not_change_categories"));
    } finally {
      setBusy(false);
    }
  }

  function saveCreate() {
    const name = draftName.trim();
    if (!name || createParentId === undefined) return;
    const siblings = managed.filter((item) => item.parentId === createParentId);
    const sortOrder = Math.max(0, ...siblings.map((item) => item.sortOrder)) + 10;
    void run(() => createKnowledgeCategory({ name, parentId: createParentId, sortOrder }));
  }

  function drop(targetId: number, position: CategoryDropPosition) {
    if (draggedId === null) return;
    const updates = planCategoryDrop(managed, draggedId, targetId, position);
    setDraggedId(null);
    if (!updates.length) return;
    void run(async () => {
      for (const update of updates) {
        await updateKnowledgeCategory(update.id, { parentId: update.parentId, sortOrder: update.sortOrder });
      }
    });
  }

  return (
    <section className="knowledge-card">
      <div className="knowledge-card-head is-plain">
        <nav className="knowledge-breadcrumbs">
          <button className="link is-strong" type="button" onClick={() => setRoute("knowledge")}>{t("common.knowledge_base")}</button>
          <span><span className="knowledge-crumb-sep">/</span><b>{t("common.categories")}</b></span>
        </nav>
        <h2>{t("common.categories")}</h2>
        <p>{t("ai.tree_up_three_levels_deep")}</p>
      </div>

      <div className="knowledge-plain-body">
        <div className="knowledge-categories-layout">
          <div className="knowledge-categories-list" aria-busy={busy}>
            {catalog.loading ? <LoadingState /> : rows.map(({ node, depth }) => {
              const block = deleteBlock(node);
              const editing = editingId === node.id;
              return (
                <div key={node.id}>
                  <div
                    className={`knowledge-category-row${editing ? " is-editing" : ""}`}
                    draggable={canManage && !node.isSystem && !editing}
                    style={{ paddingLeft: 12 + depth * 22 }}
                    onDragOver={(event) => event.preventDefault()}
                    onDragStart={() => setDraggedId(node.id)}
                    onDrop={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      drop(node.id, dropPosition(event, Boolean(node.isSystem)));
                    }}
                  >
                    <span className="knowledge-category-grip" title={t("ai.drag")}><Icon name="grip" size={15} strokeWidth={2} /></span>
                    {editing ? (
                      <>
                        <input
                          autoFocus
                          value={draftName}
                          onChange={(event) => setDraftName(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") {
                              const name = draftName.trim();
                              if (!name || name === node.name) cancel();
                              else void run(() => updateKnowledgeCategory(node.id, { name }));
                            }
                            if (event.key === "Escape") cancel();
                          }}
                        />
                        <button
                          className="knowledge-category-save"
                          disabled={!draftName.trim()}
                          type="button"
                          onClick={() => {
                            const name = draftName.trim();
                            if (!name || name === node.name) cancel();
                            else void run(() => updateKnowledgeCategory(node.id, { name }));
                          }}
                        >{t("common.done")}</button>
                        <button className="knowledge-category-cancel" type="button" onClick={cancel}>{t("common.cancel")}</button>
                      </>
                    ) : (
                      <>
                        <span className="knowledge-category-name">
                          <strong style={{ fontWeight: depth === 0 ? 600 : 500 }}>{node.name}</strong>
                          {node.isSystem && <small className="knowledge-category-tag">{t("ai.system")}</small>}
                        </span>
                        <small className="knowledge-category-count">{countLabel(node)}</small>
                        {canManage && (
                          <span className="knowledge-category-actions">
                            <button
                              disabled={depth >= 2}
                              title={depth >= 2 ? t("ai.categories_do_not_nest_deeper") : t("ai.add_nested_one")}
                              type="button"
                              onClick={() => { setEditingId(null); setCreateParentId(node.id); setDraftName(""); }}
                            >
                              <Icon name="plus" size={14} strokeWidth={2} />
                            </button>
                            <button
                              disabled={Boolean(node.isSystem)}
                              title={node.isSystem ? t("ai.system_category_cannot_renamed") : t("ai.rename")}
                              type="button"
                              onClick={() => { setCreateParentId(undefined); setEditingId(node.id); setDraftName(node.name); }}
                            >
                              <Icon name="edit" size={14} strokeWidth={1.9} />
                            </button>
                            <button
                              className={`knowledge-category-delete${block ? " is-blocked" : ""}`}
                              title={block ? t("ai.cannot_delete_because", { reason: block }) : t("ai.delete_category")}
                              type="button"
                              onClick={() => (block
                                ? setBlocked({ name: node.name, reason: block })
                                : setDeleting(node))}
                            >
                              <Icon name="trash" size={14} strokeWidth={1.9} />
                            </button>
                          </span>
                        )}
                      </>
                    )}
                  </div>
                  {createParentId === node.id && (
                    <div className="knowledge-category-row is-new" style={{ paddingLeft: 12 + (depth + 1) * 22 }}>
                      <span className="knowledge-category-grip" />
                      <input
                        autoFocus
                        placeholder={t("shared.category_name")}
                        value={draftName}
                        onChange={(event) => setDraftName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") saveCreate();
                          if (event.key === "Escape") cancel();
                        }}
                      />
                      <button className="knowledge-category-save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>{t("common.done")}</button>
                      <button className="knowledge-category-cancel" type="button" onClick={cancel}>{t("common.cancel")}</button>
                    </div>
                  )}
                </div>
              );
            })}

            {createParentId === null && (
              <div className="knowledge-category-row is-new" style={{ paddingLeft: 12 }}>
                <span className="knowledge-category-grip" />
                <input
                  autoFocus
                  placeholder={t("shared.category_name")}
                  value={draftName}
                  onChange={(event) => setDraftName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") saveCreate();
                    if (event.key === "Escape") cancel();
                  }}
                />
                <button className="knowledge-category-save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>{t("common.done")}</button>
                <button className="knowledge-category-cancel" type="button" onClick={cancel}>{t("common.cancel")}</button>
              </div>
            )}

            {canManage && (
              <div className="knowledge-categories-foot">
                <button type="button" onClick={() => { setEditingId(null); setCreateParentId(null); setDraftName(""); }}>
                  <Icon name="plus" size={14} strokeWidth={2} />{t("ai.top_level_category")}</button>
              </div>
            )}
          </div>

          <div className="knowledge-categories-side">
            <div className="knowledge-rules-card">
              <strong>{t("ai.rules")}</strong>
              <ul>
                <li>{t("ai.name_unique_within_its_parent")}</li>
                <li>{t("ai.category_cannot_moved_inside_itself")}</li>
                <li>{t("ai.only_empty_category_with_nothing")}</li>
                <li>{t("ai.no_category_system_one_cannot")}</li>
              </ul>
            </div>
            {(blocked || error) && (
              <div className="knowledge-warning-card">
                <Icon name="alert" size={16} strokeWidth={2} />
                <span>
                  {error || t("ai.cannot_delete_named", { name: blocked?.name ?? "", reason: blocked?.reason ?? "" })}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <DecisionDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        tone="danger"
        icon="trash"
        title={t("shared.delete_category")}
        description={deleting ? t("ai.category_empty_will_delete", { name: deleting.name }) : ""}
        actions={<>
          <Button variant="secondary" onClick={() => setDeleting(null)}>{t("common.cancel")}</Button>
          <Button
            variant="danger-outline"
            disabled={busy}
            onClick={() => {
              const target = deleting;
              setDeleting(null);
              if (target) void run(() => deleteKnowledgeCategory(target.id));
            }}
          >{t("common.delete")}</Button>
        </>}
      />
    </section>
  );
}
