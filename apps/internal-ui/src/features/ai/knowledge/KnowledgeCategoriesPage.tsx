import { useMemo, useState, type DragEvent } from "react";

import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { pluralRu } from "../../../shared/utils";
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

// Категории знаний (дизайн-базлайн v2, кадр KB7): отдельный экран, а не
// модалка — дерево строками с перетаскиванием, инлайн-переименованием и
// безопасным удалением. Правила и причина запрета — карточками справа.

type Row = { node: ManagedContentCategoryNode; depth: number };

function flatten(nodes: ManagedContentCategoryNode[], depth = 0): Row[] {
  return nodes.flatMap((node) => [{ node, depth }, ...flatten(node.children, depth + 1)]);
}

/** «18 знаний · 2 вложенные» — подпись строки категории. */
function countLabel(node: ManagedContentCategoryNode): string {
  if (node.count === 0 && node.children.length === 0) return "пусто";
  const knowledge = pluralRu(node.count, ["знание", "знания", "знаний"]);
  if (node.children.length === 0) return knowledge;
  return `${knowledge} · ${pluralRu(node.children.length, ["вложенная", "вложенные", "вложенных"])}`;
}

/** Почему нельзя удалить: системная, есть вложенные, есть материалы. */
function deleteBlock(node: ManagedContentCategoryNode): string | null {
  if (node.isSystem) return "системная категория";
  if (node.children.length > 0) return "есть вложенные категории";
  if (node.count > 0) return "категория не пуста";
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
      setError(caught instanceof Error ? caught.message : "Не удалось изменить категории");
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
          <button className="link is-strong" type="button" onClick={() => setRoute("knowledge")}>База знаний</button>
          <span><span className="knowledge-crumb-sep">/</span><b>Категории</b></span>
        </nav>
        <h2>Категории</h2>
        <p>Дерево до трёх уровней. Перетащите строку, чтобы сменить родителя или порядок.</p>
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
                    <span className="knowledge-category-grip" title="Перетащить"><Icon name="grip" size={15} strokeWidth={2} /></span>
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
                        >
                          Готово
                        </button>
                        <button className="knowledge-category-cancel" type="button" onClick={cancel}>Отмена</button>
                      </>
                    ) : (
                      <>
                        <span className="knowledge-category-name">
                          <strong style={{ fontWeight: depth === 0 ? 600 : 500 }}>{node.name}</strong>
                          {node.isSystem && <small className="knowledge-category-tag">системная</small>}
                        </span>
                        <small className="knowledge-category-count">{countLabel(node)}</small>
                        {canManage && (
                          <span className="knowledge-category-actions">
                            <button
                              disabled={depth >= 2}
                              title={depth >= 2 ? "Глубже трёх уровней категории не вкладываются" : "Добавить вложенную"}
                              type="button"
                              onClick={() => { setEditingId(null); setCreateParentId(node.id); setDraftName(""); }}
                            >
                              <Icon name="plus" size={14} strokeWidth={2} />
                            </button>
                            <button
                              disabled={Boolean(node.isSystem)}
                              title={node.isSystem ? "Системную категорию нельзя переименовать" : "Переименовать"}
                              type="button"
                              onClick={() => { setCreateParentId(undefined); setEditingId(node.id); setDraftName(node.name); }}
                            >
                              <Icon name="edit" size={14} strokeWidth={1.9} />
                            </button>
                            <button
                              className={`knowledge-category-delete${block ? " is-blocked" : ""}`}
                              title={block ? `Удалить нельзя: ${block}` : "Удалить категорию"}
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
                        placeholder="Название категории"
                        value={draftName}
                        onChange={(event) => setDraftName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") saveCreate();
                          if (event.key === "Escape") cancel();
                        }}
                      />
                      <button className="knowledge-category-save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>Готово</button>
                      <button className="knowledge-category-cancel" type="button" onClick={cancel}>Отмена</button>
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
                  placeholder="Название категории"
                  value={draftName}
                  onChange={(event) => setDraftName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") saveCreate();
                    if (event.key === "Escape") cancel();
                  }}
                />
                <button className="knowledge-category-save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>Готово</button>
                <button className="knowledge-category-cancel" type="button" onClick={cancel}>Отмена</button>
              </div>
            )}

            {canManage && (
              <div className="knowledge-categories-foot">
                <button type="button" onClick={() => { setEditingId(null); setCreateParentId(null); setDraftName(""); }}>
                  <Icon name="plus" size={14} strokeWidth={2} />Категория верхнего уровня
                </button>
              </div>
            )}
          </div>

          <div className="knowledge-categories-side">
            <div className="knowledge-rules-card">
              <strong>Правила</strong>
              <ul>
                <li>Имя уникально внутри родителя.</li>
                <li>Категорию нельзя перенести внутрь себя.</li>
                <li>Удаление — только для пустой категории без вложенных.</li>
                <li>«Без категории» системная: не переименовывается и не удаляется.</li>
              </ul>
            </div>
            {(blocked || error) && (
              <div className="knowledge-warning-card">
                <Icon name="alert" size={16} strokeWidth={2} />
                <span>
                  {error || `«${blocked?.name}» удалить нельзя: ${blocked?.reason}. Сначала перенесите содержимое.`}
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
        title="Удалить категорию?"
        description={deleting ? `Категория «${deleting.name}» пуста и будет удалена.` : ""}
        actions={<>
          <Button variant="secondary" onClick={() => setDeleting(null)}>Отмена</Button>
          <Button
            variant="danger-outline"
            disabled={busy}
            onClick={() => {
              const target = deleting;
              setDeleting(null);
              if (target) void run(() => deleteKnowledgeCategory(target.id));
            }}
          >
            Удалить
          </Button>
        </>}
      />
    </section>
  );
}
