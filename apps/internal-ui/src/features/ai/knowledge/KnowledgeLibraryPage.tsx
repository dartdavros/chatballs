import { Dropdown } from "antd";
import { useMemo, useState } from "react";

import { hasCapability } from "../../../auth/access";
import { Pagination } from "../../../shared/Pagination";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button, FilterDropdown, SearchInput } from "../../../shared/ui-controls";
import { pluralRu } from "../../../shared/utils";
import type { RouteKey, SessionUser } from "../../../types";
import type { AgentRef } from "../../agents/model";
import { KnowledgeAgentDialog } from "./KnowledgeAgentDialog";
import { KnowledgeBulkBar } from "./KnowledgeBulkBar";
import { KnowledgeCategoryDialog } from "./KnowledgeCategoryDialog";
import {
  answerStateLabel,
  categoryBranch,
  categoryRows,
  knowledgeUpdatedAt,
  libraryTotals,
} from "./knowledgeLibraryModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import {
  bulkMoveKnowledge,
  deleteKnowledgeItem,
  linkKnowledgeToAgent,
  reindexKnowledge,
  updateKnowledgeItem,
  type KnowledgeItem,
} from "./model";
import { useKnowledgeLibrary } from "./useKnowledgeLibrary";

// Библиотека знаний (дизайн-базлайн v2, кадры KB1, KB2, KB3, KB9): шапка с
// состоянием индекса, дерево категорий 260px, таблица материалов. Панель
// массовых операций живёт, пока живо выделение.

const KNOWLEDGE_FORMS: [string, string, string] = ["знание", "знания", "знаний"];

const ANSWER_FILTER = [
  { value: "true", label: "Включено" },
  { value: "false", label: "Выключено" },
];

export function KnowledgeLibraryPage({
  agents,
  openKnowledge,
  openKnowledgeEditor,
  setRoute,
  user,
}: {
  agents: AgentRef[];
  openKnowledge: (knowledgeId: number) => void;
  openKnowledgeEditor: (knowledgeId: number | null) => void;
  setRoute: (route: RouteKey) => void;
  user: SessionUser;
}) {
  const library = useKnowledgeLibrary();
  const canManage = hasCapability(user, "ai.manage");
  const [answerOpen, setAnswerOpen] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const [attachOpen, setAttachOpen] = useState(false);
  const [movingOpen, setMovingOpen] = useState(false);
  const [deleting, setDeleting] = useState<{ ids: number[]; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const rows = useMemo(() => categoryRows(library.categories), [library.categories]);
  const selectedCategory = library.filters.category;

  const selected = [...library.selectedIds];
  const selectedItems = library.items.filter((item) => library.selectedIds.has(item.id));
  const allVisibleChecked = library.items.length > 0 && library.items.every((item) => library.selectedIds.has(item.id));
  const activeCategory = selectedCategory === undefined
    ? null
    : library.categories.find((category) => category.id === selectedCategory) ?? null;
  const agentFilter = library.filters.agents;
  const filtersActive = Boolean(library.filters.search.trim())
    || library.filters.isEnabled !== undefined
    || agentFilter.length > 0;

  const scopeNote = selected.length > 0
    ? `выбрано ${selected.length} из ${library.total}`
    : activeCategory
      ? `категория «${activeCategory.name}»`
      : "показаны все категории";

  async function run(action: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setError("");
    try {
      await action();
      await library.reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : fallback);
    } finally {
      setBusy(false);
    }
  }

  async function attachToAgent(agentId: number, action: "attach" | "detach") {
    await run(
      () => linkKnowledgeToAgent({ agentId, action, knowledgeIds: selected }),
      "Не удалось изменить знания агента",
    );
    setAttachOpen(false);
    library.clearSelected();
  }

  async function moveSelected(categoryId: number) {
    await run(
      () => bulkMoveKnowledge({ knowledgeIds: selected, categoryId }),
      "Не удалось переместить знания",
    );
    setMovingOpen(false);
    library.clearSelected();
  }

  async function setEnabled(ids: number[], isEnabled: boolean) {
    await run(
      async () => { for (const id of ids) await updateKnowledgeItem(id, { isEnabled }); },
      "Не удалось изменить участие в ответах",
    );
    library.clearSelected();
  }

  const stats = libraryTotals(library.categories, library.items);

  return (
    <section className="knowledge-card">
      <div className="knowledge-card-head">
        <div className="knowledge-card-head-row">
          <div className="knowledge-card-identity">
            <div className="knowledge-card-title">
              <h2>База знаний</h2>
              <span className="knowledge-index-pill"><i />Индекс актуален</span>
              <span>{stats}</span>
            </div>
            <p>
              Материалы для AI-агентов: регламенты, прайсы, скрипты. Агент отвечает только по
              включённым знаниям, которые к нему прикреплены. Клиент их не видит — публичное
              живёт в порталах.
            </p>
          </div>
          <div className="knowledge-card-actions">
            {canManage && (
              <Button variant="secondary" className="knowledge-secondary-action" icon="import" onClick={() => setRoute("knowledgeImport")}>
                Импорт YAML
              </Button>
            )}
            {canManage && (
              <Button variant="primary" className="knowledge-primary-action" icon="plus" onClick={() => openKnowledgeEditor(null)}>
                Добавить знание
              </Button>
            )}
            <Dropdown
              menu={{ items: [
                { key: "categories", label: <button type="button" onClick={() => setRoute("knowledgeCategories")}><Icon name="folder" size={15} strokeWidth={1.9} />Категории</button> },
                { key: "import", label: <button type="button" onClick={() => setRoute("knowledgeImport")}><Icon name="import" size={15} strokeWidth={1.9} />Импорт YAML</button> },
              ] }}
              overlayClassName="app-dropdown is-knowledge-menu"
              placement="bottomRight"
              trigger={["click"]}
            >
              <button aria-label="Ещё" className="knowledge-more-button" title="Ещё" type="button">
                <Icon name="more" size={16} strokeWidth={2} />
              </button>
            </Dropdown>
          </div>
        </div>
      </div>

      {error && <div className="knowledge-form-error">{error}</div>}

      <div className="knowledge-library">
        <aside className="knowledge-sections">
          <header>
            <span>КАТЕГОРИИ</span>
            {canManage && <button type="button" onClick={() => setRoute("knowledgeCategories")}>Управлять</button>}
          </header>
          <nav>
            <button
              className={`knowledge-section-row${selectedCategory === undefined ? " is-active" : ""}`}
              style={{ paddingLeft: 9 }}
              type="button"
              onClick={() => library.updateFilter("category", undefined)}
            >
              <Icon name="folder" size={15} strokeWidth={1.8} />
              <span>Все знания</span>
              <small>{library.categories.filter((item) => item.parentId === null).reduce((total, item) => total + (item.knowledgeCount ?? 0), 0)}</small>
            </button>
            {rows.map(({ category, depth, count }) => (
              <button
                className={`knowledge-section-row${selectedCategory === category.id ? " is-active" : ""}`}
                key={category.id}
                style={{ paddingLeft: 9 + depth * 16 }}
                type="button"
                onClick={() => library.updateFilter("category", category.id)}
              >
                <span>{category.name}</span>
                <small>{count}</small>
              </button>
            ))}
          </nav>
          {canManage && (
            <div className="knowledge-sections-foot">
              <button type="button" onClick={() => setRoute("knowledgeCategories")}>
                <Icon name="plus" size={14} strokeWidth={2} />Добавить категорию
              </button>
            </div>
          )}
        </aside>

        <div className="knowledge-library-main">
          <div className="knowledge-library-inner">
            <div className="knowledge-library-toolbar">
              <SearchInput
                className="knowledge-library-search"
                placeholder="Поиск по заголовку и описанию"
                value={library.filters.search}
                onChange={(value) => library.updateFilter("search", value)}
              />
              <FilterDropdown
                caption="В ответах:"
                label={library.filters.isEnabled === undefined ? "Все" : library.filters.isEnabled ? "Включено" : "Выключено"}
                open={answerOpen}
                options={ANSWER_FILTER}
                selected={library.filters.isEnabled === undefined ? [] : [String(library.filters.isEnabled)]}
                onOpenChange={setAnswerOpen}
                onSelect={(value) => {
                  library.updateFilter("isEnabled", library.filters.isEnabled === (value === "true") ? undefined : value === "true");
                }}
              />
              <FilterDropdown
                caption="Агент:"
                label={agentFilter.length === 1 ? agents.find((agent) => agent.aiAgentId === agentFilter[0])?.name ?? "Любой" : "Любой"}
                multiple
                open={agentOpen}
                options={agents.filter((agent) => agent.aiAgentId != null).map((agent) => ({ value: String(agent.aiAgentId), label: agent.name }))}
                selected={agentFilter.map(String)}
                onOpenChange={setAgentOpen}
                onSelect={(value) => {
                  const id = Number(value);
                  library.updateFilter("agents", agentFilter.includes(id)
                    ? agentFilter.filter((item) => item !== id)
                    : [...agentFilter, id]);
                }}
              />
              <span className="knowledge-library-toolbar-gap" />
              <span className="knowledge-scope-note">{scopeNote}</span>
            </div>

            {library.itemsLoading ? (
              <LoadingState />
            ) : library.items.length === 0 ? (
              <div className="knowledge-empty">
                <div>
                  <span className="knowledge-empty-icon"><Icon name="book" size={25} strokeWidth={1.7} /></span>
                  <h3>
                    {activeCategory && !filtersActive
                      ? `В категории «${activeCategory.name}» пока нет знаний`
                      : filtersActive ? "Под фильтры ничего не подошло" : "Знаний пока нет"}
                  </h3>
                  <p>
                    {filtersActive
                      ? "Снимите фильтры или измените запрос — материалы могли остаться в других категориях."
                      : "Добавьте материал вручную или загрузите пачкой из YAML. Пустую категорию без вложенных можно удалить в «Управлять»."}
                  </p>
                  {canManage && !filtersActive && (
                    <div className="knowledge-empty-actions">
                      <Button variant="primary" onClick={() => openKnowledgeEditor(null)}>Добавить знание</Button>
                      <Button variant="secondary" onClick={() => setRoute("knowledgeImport")}>Импорт YAML</Button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                <table className="knowledge-table">
                  <thead>
                    <tr>
                      <th className="knowledge-check-cell">
                        {canManage && (
                          <button
                            aria-label="Выбрать все знания на странице"
                            className={`knowledge-check${allVisibleChecked ? " is-checked" : ""}`}
                            type="button"
                            onClick={library.toggleVisible}
                          >
                            {allVisibleChecked && <Icon name="check" size={11} strokeWidth={3.2} />}
                          </button>
                        )}
                      </th>
                      <th>ЗНАНИЕ</th>
                      <th>КАТЕГОРИЯ</th>
                      <th>ФРАГМЕНТЫ</th>
                      <th>АГЕНТЫ</th>
                      <th>В ОТВЕТАХ</th>
                      <th>ОБНОВЛЕНО</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {library.items.map((item) => {
                      const checked = library.selectedIds.has(item.id);
                      const path = knowledgeCategoryPath(library.categories, item.category.id);
                      const parent = path.includes(" / ") ? path.slice(0, path.lastIndexOf(" / ")) : "";
                      // Сколько агентов используют материал — считает сервер.
                      const attachedAgents = item.agentsCount ?? 0;
                      const menuItems = [
                        { key: "open", label: <button type="button" onClick={() => openKnowledge(item.id)}><Icon name="book" size={15} strokeWidth={1.8} />Открыть знание</button> },
                        ...(canManage ? [
                          { key: "edit", label: <button type="button" onClick={() => openKnowledgeEditor(item.id)}><Icon name="edit" size={15} strokeWidth={1.9} />Редактировать</button> },
                          { key: "divider-1", type: "divider" as const },
                          { key: "agent", label: <button type="button" onClick={() => { library.selectOnly(item.id); setAttachOpen(true); }}><Icon name="robot" size={15} strokeWidth={1.8} />Прикрепить к агенту</button> },
                          { key: "move", label: <button type="button" onClick={() => { library.selectOnly(item.id); setMovingOpen(true); }}><Icon name="move" size={15} strokeWidth={1.9} />Переместить в категорию</button> },
                          { key: "answers", label: <button type="button" onClick={() => void setEnabled([item.id], !item.isEnabled)}><Icon name={item.isEnabled ? "eyeOff" : "eye"} size={15} strokeWidth={1.9} />{item.isEnabled ? "Выключить в ответах" : "Включить в ответах"}</button> },
                          { key: "reindex", label: <button type="button" onClick={() => void run(() => reindexKnowledge(item.id), "Не удалось переиндексировать знание")}><Icon name="undo" size={15} strokeWidth={1.9} />Переиндексировать</button> },
                          { key: "divider-2", type: "divider" as const },
                          { key: "delete", label: <button className="danger" type="button" onClick={() => setDeleting({ ids: [item.id], text: `«${item.title}» и его вложения будут удалены. У агентов, которым знание прикреплено, оно исчезнет из ответов.` })}><Icon name="trash" size={15} strokeWidth={1.9} />Удалить знание</button> },
                        ] : []),
                      ];
                      return (
                        <tr
                          className={`knowledge-row${checked ? " is-checked" : ""}${item.isEnabled ? "" : " is-off"}`}
                          key={item.id}
                          onClick={() => openKnowledge(item.id)}
                        >
                          <td className="knowledge-check-cell" onClick={(event) => event.stopPropagation()}>
                            {canManage && (
                              <button
                                aria-label={`Выбрать «${item.title}»`}
                                className={`knowledge-check${checked ? " is-checked" : ""}`}
                                type="button"
                                onClick={() => library.toggleSelected(item.id)}
                              >
                                {checked && <Icon name="check" size={11} strokeWidth={3.2} />}
                              </button>
                            )}
                          </td>
                          <td>
                            <span className="knowledge-name">
                              <i><Icon name="book" size={14} strokeWidth={1.8} /></i>
                              <span>
                                <strong>{item.title}</strong>
                                <small>{item.description}</small>
                              </span>
                              {item.attachments.length > 0 && (
                                <small className="knowledge-name-files" title="Вложения">
                                  <Icon name="attach" size={12} strokeWidth={1.9} />{item.attachments.length}
                                </small>
                              )}
                            </span>
                          </td>
                          <td className="knowledge-cell-category">
                            {item.category.name}
                            {parent && <small>{parent}</small>}
                          </td>
                          <td className="knowledge-cell-fragments">{item.fragmentsCount ?? "—"}</td>
                          <td>
                            {attachedAgents > 0
                              ? <span className="knowledge-agents-tag"><Icon name="robot" size={12} strokeWidth={1.8} />{attachedAgents}</span>
                              : <small className="knowledge-agents-empty">не прикреплено</small>}
                          </td>
                          <td>
                            <span className={`knowledge-answer-pill${item.isEnabled ? " is-on" : ""}`}><i />{answerStateLabel(item)}</span>
                          </td>
                          <td className="knowledge-cell-updated">
                            {knowledgeUpdatedAt(item)}
                            {item.updatedBy && <small>{item.updatedBy}</small>}
                          </td>
                          <td className="row-actions" onClick={(event) => event.stopPropagation()}>
                            <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-knowledge-menu" placement="bottomRight" trigger={["click"]}>
                              <button aria-label={`Действия: ${item.title}`} className="row-menu-button" type="button"><Icon name="more" size={16} strokeWidth={2} /></button>
                            </Dropdown>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                <Pagination
                  note={`${pluralRu(library.total, KNOWLEDGE_FORMS)} · показаны ${library.items.length} · агент отвечает только по включённым и прикреплённым`}
                  page={library.page}
                  pageCount={library.pageCount}
                  onPage={library.setPage}
                />
              </>
            )}
          </div>
        </div>
      </div>

      {selected.length > 0 && (
        <KnowledgeBulkBar
          busy={busy}
          count={selected.length}
          onAttach={() => setAttachOpen(true)}
          onClear={library.clearSelected}
          onDisable={() => void setEnabled(selected, false)}
          onEnable={() => void setEnabled(selected, true)}
          onMove={() => setMovingOpen(true)}
          onRemove={() => setDeleting({
            ids: selected,
            text: `${pluralRu(selected.length, KNOWLEDGE_FORMS)} и их вложения будут удалены. У агентов, которым они прикреплены, материалы исчезнут из ответов.`,
          })}
        />
      )}

      {attachOpen && (
        <KnowledgeAgentDialog
          agents={agents}
          busy={busy}
          items={selectedItems}
          onCancel={() => setAttachOpen(false)}
          onSubmit={(agentId, action) => void attachToAgent(agentId, action)}
        />
      )}

      {movingOpen && (
        <KnowledgeCategoryDialog
          busy={busy}
          categories={library.categories}
          count={selected.length}
          onCancel={() => setMovingOpen(false)}
          onSubmit={(categoryId) => void moveSelected(categoryId)}
        />
      )}

      <DecisionDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        tone="danger"
        icon="trash"
        title={deleting && deleting.ids.length > 1 ? "Удалить выбранные знания?" : "Удалить знание?"}
        description={deleting?.text ?? ""}
        actions={<>
          <Button variant="secondary" onClick={() => setDeleting(null)}>Отмена</Button>
          <Button
            variant="danger-outline"
            disabled={busy}
            onClick={() => {
              const target = deleting;
              setDeleting(null);
              if (!target) return;
              void run(
                async () => { for (const id of target.ids) await deleteKnowledgeItem(id); },
                "Не удалось удалить знание",
              ).then(() => library.clearSelected());
            }}
          >
            Удалить
          </Button>
        </>}
      />
    </section>
  );
}
