import { Dropdown } from "antd";
import { useCallback, useEffect, useState } from "react";

import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button, CopyButton } from "../../../shared/ui-controls";
import { pluralRu, shortDateTime } from "../../../shared/utils";
import type { RouteKey } from "../../../types";
import type { AgentRef } from "../../agents/model";
import { MarkdownContent } from "../../help-center/MarkdownContent";
import { KnowledgeAgentDialog } from "./KnowledgeAgentDialog";
import { KnowledgeCategoryDialog } from "./KnowledgeCategoryDialog";
import {
  agentStates,
  attachmentMeta,
  isImageAttachment,
} from "./knowledgeLibraryModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import {
  bulkMoveKnowledge,
  deleteKnowledgeItem,
  fetchKnowledgeItem,
  linkKnowledgeToAgent,
  reindexKnowledge,
  updateKnowledgeItem,
  type KnowledgeItem,
} from "./model";
import { useKnowledgeCategories } from "./useKnowledgeCategories";

// Карточка знания (дизайн-базлайн v2, кадр KB4): шапка как у портала —
// состояние в ответах, фрагменты и агенты чипами; тело — содержимое до 720px
// и рейка 320px с категорией, вложениями, агентами и индексацией.

export function KnowledgeCardPage({
  agents,
  canManage,
  knowledgeId,
  openKnowledgeEditor,
  reloadAgents,
  setRoute,
}: {
  agents: AgentRef[];
  canManage: boolean;
  knowledgeId: number | null;
  openKnowledgeEditor: (knowledgeId: number | null) => void;
  reloadAgents: () => void;
  setRoute: (route: RouteKey) => void;
}) {
  const catalog = useKnowledgeCategories();
  const [item, setItem] = useState<KnowledgeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attachOpen, setAttachOpen] = useState(false);
  const [movingOpen, setMovingOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const load = useCallback(async () => {
    if (!knowledgeId) return;
    setLoading(true);
    setFailed(false);
    try {
      const { knowledge } = await fetchKnowledgeItem(knowledgeId);
      setItem(knowledge);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [knowledgeId]);

  useEffect(() => { void load(); }, [load]);

  async function run(action: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
      reloadAgents();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : fallback);
    } finally {
      setBusy(false);
    }
  }

  if (!knowledgeId) return <div className="knowledge-card"><EmptyState title="Знание не выбрано" /></div>;
  if (loading || catalog.loading) return <div className="knowledge-card"><LoadingState /></div>;
  if (failed || catalog.error || !item) return <div className="knowledge-card"><EmptyState title="Не удалось загрузить знание" /></div>;

  const path = knowledgeCategoryPath(catalog.categories, item.category.id);
  const crumbs = path ? path.split(" / ") : [item.category.name];
  const attached = agentStates(item.agents ?? []);
  const fragments = item.fragmentsCount ?? 0;
  const characters = (item.content ?? "").length;

  const menuItems = canManage ? [
    { key: "move", label: <button type="button" onClick={() => setMovingOpen(true)}><Icon name="move" size={15} strokeWidth={1.9} />Переместить в категорию</button> },
    { key: "answers", label: <button type="button" onClick={() => void run(() => updateKnowledgeItem(item.id, { isEnabled: !item.isEnabled }), "Не удалось изменить участие в ответах")}><Icon name={item.isEnabled ? "eyeOff" : "eye"} size={15} strokeWidth={1.9} />{item.isEnabled ? "Выключить в ответах" : "Включить в ответах"}</button> },
    { key: "reindex", label: <button type="button" onClick={() => void run(() => reindexKnowledge(item.id), "Не удалось переиндексировать знание")}><Icon name="undo" size={15} strokeWidth={1.9} />Переиндексировать</button> },
    { key: "divider", type: "divider" as const },
    { key: "delete", label: <button className="danger" type="button" onClick={() => setDeleteOpen(true)}><Icon name="trash" size={15} strokeWidth={1.9} />Удалить знание</button> },
  ] : [];

  return (
    <section className="knowledge-card">
      <div className="knowledge-card-head">
        <nav className="knowledge-breadcrumbs">
          <button className="link is-strong" type="button" onClick={() => setRoute("knowledge")}>База знаний</button>
          {crumbs.map((crumb, index) => (
            <span key={`${crumb}-${index}`}>
              <span className="knowledge-crumb-sep">/</span>
              {index === crumbs.length - 1 ? <b>{crumb}</b> : <span>{crumb}</span>}
            </span>
          ))}
        </nav>
        <div className="knowledge-card-head-row">
          <div className="knowledge-card-identity">
            <div className="knowledge-card-title">
              <h2>{item.title}</h2>
              <span className={`knowledge-answer-pill${item.isEnabled ? " is-on" : ""}`}>
                <i />{item.isEnabled ? "В ответах агента" : "Не участвует в ответах"}
              </span>
            </div>
            <div className="knowledge-card-chips">
              <span className="knowledge-chip">
                <Icon name="box" size={14} strokeWidth={1.9} />
                {pluralRu(fragments, ["фрагмент", "фрагмента", "фрагментов"])} · пересобраны {shortDateTime(item.updatedAt)}
              </span>
              <span className="knowledge-chip">
                <Icon name="robot" size={14} strokeWidth={1.9} />
                {pluralRu(attached.length, ["агент", "агента", "агентов"])}
              </span>
              {item.updatedBy && <span className="knowledge-card-author">обновил {item.updatedBy} · {shortDateTime(item.updatedAt)}</span>}
            </div>
          </div>
          <div className="knowledge-card-actions">
            {canManage && (
              <Button variant="secondary" className="knowledge-secondary-action" icon="robot" onClick={() => setAttachOpen(true)}>
                Прикрепить к агенту
              </Button>
            )}
            {canManage && (
              <Button variant="primary" className="knowledge-primary-action" icon="edit" onClick={() => openKnowledgeEditor(item.id)}>
                Редактировать
              </Button>
            )}
            {canManage && (
              <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-knowledge-menu" placement="bottomRight" trigger={["click"]}>
                <button aria-label="Ещё" className="knowledge-more-button" title="Ещё" type="button">
                  <Icon name="more" size={16} strokeWidth={2} />
                </button>
              </Dropdown>
            )}
          </div>
        </div>
      </div>

      {error && <div className="knowledge-form-error">{error}</div>}

      <div className="knowledge-card-body">
        <div className="knowledge-card-content">
          <article>
            {item.description && <p className="knowledge-card-lead">{item.description}</p>}
            <MarkdownContent content={item.content ?? ""} />
          </article>
        </div>

        <aside className="knowledge-rail">
          <div className="knowledge-rail-block is-top">
            <div>
              <span className="knowledge-rail-label">КАТЕГОРИЯ</span>
              <span className="knowledge-rail-category">
                <Icon name="folder" size={13} strokeWidth={1.8} />{path || item.category.name}
              </span>
            </div>
            <div className="knowledge-rail-toggle">
              <span>
                <strong>Участвует в ответах</strong>
                <small>выключенное знание не попадает в retrieval</small>
              </span>
              <button
                aria-label="Участвует в ответах"
                aria-pressed={item.isEnabled}
                className={`knowledge-switch${item.isEnabled ? " is-on" : ""}`}
                disabled={!canManage || busy}
                type="button"
                onClick={() => void run(() => updateKnowledgeItem(item.id, { isEnabled: !item.isEnabled }), "Не удалось изменить участие в ответах")}
              >
                <i />
              </button>
            </div>
          </div>

          <div className="knowledge-rail-block">
            <div className="knowledge-rail-head">
              <span>ВЛОЖЕНИЯ</span>
              <small>ссылки уходят в ответ агента</small>
            </div>
            <div className="knowledge-rail-files">
              {item.attachments.map((attachment) => (
                <div className="knowledge-rail-file" key={attachment.id}>
                  <i><Icon name={isImageAttachment(attachment) ? "image" : "file"} size={14} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{attachment.name}</strong>
                    <small>{attachmentMeta(attachment, item.content ?? "")}</small>
                  </span>
                  <CopyButton className="knowledge-rail-file-copy" label="" value={attachment.url} />
                </div>
              ))}
              {item.attachments.length === 0 && <p className="knowledge-rail-empty">Вложений нет.</p>}
            </div>
          </div>

          <div className="knowledge-rail-block">
            <div className="knowledge-rail-head">
              <span>АГЕНТЫ</span>
              {canManage && <button type="button" onClick={() => setAttachOpen(true)}>Изменить</button>}
            </div>
            <div className="knowledge-rail-agents">
              {attached.map(({ agent, meta, answering }) => (
                <div className="knowledge-rail-agent" key={agent.id}>
                  <i className={answering ? "is-answering" : ""}><Icon name="robot" size={13} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{agent.name}</strong>
                    <small>{meta}</small>
                  </span>
                  <small className={`knowledge-agent-state${answering ? " is-on" : ""}`}>{answering ? "активен" : "не в ответах"}</small>
                </div>
              ))}
              {attached.length === 0 && <p className="knowledge-rail-empty">Знание не прикреплено ни к одному агенту — в ответах оно не используется.</p>}
            </div>
          </div>

          <div className="knowledge-rail-block">
            <span className="knowledge-rail-label">ИНДЕКСАЦИЯ</span>
            <div className="knowledge-index-box">
              <div className="knowledge-index-count">
                <strong>{fragments}</strong>
                <span>фрагментов · {characters.toLocaleString("ru-RU")} знаков</span>
              </div>
              <p>Фрагменты пересобираются при сохранении. Пока идёт пересборка, агент отвечает по прежней версии.</p>
              {canManage && (
                <button
                  className="knowledge-reindex-button"
                  disabled={busy}
                  type="button"
                  onClick={() => void run(() => reindexKnowledge(item.id), "Не удалось переиндексировать знание")}
                >
                  <Icon name="undo" size={13} strokeWidth={1.9} />Переиндексировать
                </button>
              )}
            </div>
          </div>
        </aside>
      </div>

      {attachOpen && (
        <KnowledgeAgentDialog
          agents={agents}
          busy={busy}
          items={[item]}
          onCancel={() => setAttachOpen(false)}
          onSubmit={(agentId, mode) => {
            setAttachOpen(false);
            void run(
              () => linkKnowledgeToAgent({ agentId, action: mode, knowledgeIds: [item.id] }),
              "Не удалось изменить знания агента",
            );
          }}
        />
      )}

      {movingOpen && (
        <KnowledgeCategoryDialog
          busy={busy}
          categories={catalog.categories}
          count={1}
          onCancel={() => setMovingOpen(false)}
          onSubmit={(categoryId) => {
            setMovingOpen(false);
            void run(
              async () => {
                await bulkMoveKnowledge({ knowledgeIds: [item.id], categoryId });
                await catalog.reload();
              },
              "Не удалось переместить знание",
            );
          }}
        />
      )}

      <DecisionDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        tone="danger"
        icon="trash"
        title="Удалить знание?"
        description={`«${item.title}» и его вложения будут удалены. У агентов, которым знание прикреплено, оно исчезнет из ответов.`}
        actions={<>
          <Button variant="secondary" onClick={() => setDeleteOpen(false)}>Отмена</Button>
          <Button
            variant="danger-outline"
            disabled={busy}
            onClick={() => {
              setDeleteOpen(false);
              setBusy(true);
              void deleteKnowledgeItem(item.id)
                .then(() => setRoute("knowledge"))
                .catch(() => { setError("Не удалось удалить знание"); setBusy(false); });
            }}
          >
            Удалить
          </Button>
        </>}
      />
    </section>
  );
}
