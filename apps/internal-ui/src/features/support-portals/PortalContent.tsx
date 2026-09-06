import { useMemo, useState } from "react";

import {
  AgentLinkDialog,
  type AgentLinkAction,
  type AgentLinkOutcome,
} from "../../shared/content-library/AgentLinkDialog";
import { BulkSelectionBar } from "../../shared/content-library/BulkSelectionBar";
import { CategoryTree } from "../../shared/content-library/CategoryTree";
import { ContentLibraryTable } from "../../shared/content-library/ContentLibraryTable";
import { ContentLibraryToolbar } from "../../shared/content-library/ContentLibraryToolbar";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { pluralRu } from "../../shared/utils";
import { ARTICLE_STATUS_LABEL } from "./model";
import { agentLinkOptions } from "../ai/agentOptions";
import { linkPortalArticlesToAgent } from "../ai/knowledge/model";
import { useAiAgents } from "../ai/useAiAgents";
import { PortalArticleEditor } from "./PortalArticleEditor";
import { PortalArticleImportModal } from "./PortalArticleImportModal";
import { PortalArticleTable } from "./PortalArticleTable";
import { PortalCategoryManagement } from "./PortalCategoryManagement";
import {
  archivePortalArticle,
  portalErrorMessage,
  publishArticleRevision,
  type PortalArticle,
  type PortalCategory,
} from "./model";

type Decision = {
  article: PortalArticle;
  revisionId?: number;
  type: "archive" | "publish";
};

const ARTICLE_FORMS: [string, string, string] = ["статья", "статьи", "статей"];

export function PortalContent({
  articles,
  canLinkAgents,
  canManage,
  categories,
  locale,
  portalId,
  reload,
}: {
  articles: PortalArticle[];
  canLinkAgents: boolean;
  canManage: boolean;
  categories: PortalCategory[];
  locale: string;
  portalId: number;
  reload: () => Promise<void>;
}) {
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [agentOpen, setAgentOpen] = useState(false);
  const [outcome, setOutcome] = useState<AgentLinkOutcome | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState<PortalArticle | null | undefined>(undefined);
  const [managingCategories, setManagingCategories] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const filtered = useMemo(() => {
    const childIds = new Set<number>();
    if (selectedCategory !== undefined) {
      const pending = [selectedCategory];
      while (pending.length) {
        const id = pending.pop()!;
        childIds.add(id);
        categories.filter((item) => item.parentId === id).forEach((item) => pending.push(item.id));
      }
    }
    const normalized = query.trim().toLocaleLowerCase();
    return articles.filter((article) => (
      (selectedCategory === undefined || childIds.has(article.category.id))
      && (!language || article.locale === language)
      && (!status || article.status === status)
      && (!normalized || [
        article.slug,
        article.latestRevision?.title,
        article.latestRevision?.summary,
      ].some((value) => value?.toLocaleLowerCase().includes(normalized)))
    ));
  }, [articles, categories, language, query, selectedCategory, status]);

  const { agents } = useAiAgents();
  const bulkMode = selectedIds.size > 0;

  function toggleSelected(articleId: number) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(articleId)) next.delete(articleId);
      else next.add(articleId);
      return next;
    });
  }

  function toggleVisible() {
    setSelectedIds((current) => (
      filtered.every((article) => current.has(article.id))
        ? new Set()
        : new Set(filtered.map((article) => article.id))
    ));
  }

  async function submitAgentLink(agentId: number, action: AgentLinkAction) {
    setBusy(true);
    setAgentError(null);
    try {
      const result = await linkPortalArticlesToAgent({ agentId, action, articleIds: [...selectedIds] });
      setOutcome({ action, changed: result.changed, skipped: result.skippedIds.length });
    } catch (caught) {
      setAgentError(portalErrorMessage(caught, "Не удалось изменить статьи агента"));
    } finally {
      setBusy(false);
    }
  }

  async function applyDecision() {
    if (!decision) return;
    setBusy(true);
    setError("");
    try {
      if (decision.type === "archive") {
        await archivePortalArticle(portalId, decision.article.id);
      } else if (decision.revisionId) {
        await publishArticleRevision(portalId, decision.article.id, decision.revisionId);
      }
      setDecision(null);
      setEditing(undefined);
      await reload();
    } catch (caught) {
      setError(portalErrorMessage(caught, "Не удалось изменить статью"));
      setDecision(null);
    } finally {
      setBusy(false);
    }
  }

  if (editing !== undefined) {
    return (
      <PortalArticleEditor
        article={editing}
        categories={categories}
        defaultLocale={locale}
        portalId={portalId}
        onClose={() => setEditing(undefined)}
        onPublish={(article, revisionId) => setDecision({ article, revisionId, type: "publish" })}
        onSaved={reload}
      />
    );
  }

  return (
    <>
      <div className="knowledge-library-layout">
        <CategoryTree
          allLabel="Все материалы"
          canManage={canManage}
          categories={categories.map((category) => ({
            id: category.id,
            name: category.name,
            parentId: category.parentId,
            count: category.articleCount,
          }))}
          error={false}
          loading={false}
          selectedId={selectedCategory}
          onManage={() => setManagingCategories(true)}
          onRetry={() => void reload()}
          onSelect={setSelectedCategory}
        />
        <main className="knowledge-library-list">
          {bulkMode ? (
            <BulkSelectionBar count={selectedIds.size} forms={ARTICLE_FORMS} onClear={() => setSelectedIds(new Set())}>
              {canLinkAgents && (
                <button type="button" onClick={() => { setAgentOpen(true); setOutcome(null); setAgentError(null); }}>
                  <Icon name="robot" size={15} />Прикрепить к агенту
                </button>
              )}
            </BulkSelectionBar>
          ) : (
          <ContentLibraryToolbar
            query={query}
            onQueryChange={setQuery}
            action={canManage && categories.length > 0 && (
              <>
                <Button variant="secondary" icon="download" onClick={() => setImportOpen(true)}>Импорт YAML</Button>
                <Button variant="primary" icon="plus" onClick={() => setEditing(null)}>Новая статья</Button>
              </>
            )}
          >
            <label className="knowledge-filter-select"><span>Язык:</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">Все</option><option value="ru">Русский</option><option value="en">English</option></select></label>
            <label className="knowledge-filter-select"><span>Статус:</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Все</option><option value="DRAFT">{ARTICLE_STATUS_LABEL.DRAFT}</option><option value="PUBLISHED">{ARTICLE_STATUS_LABEL.PUBLISHED}</option><option value="ARCHIVED">{ARTICLE_STATUS_LABEL.ARCHIVED}</option></select></label>
          </ContentLibraryToolbar>
          )}
          {error && <div className="portal-form-error">{error}</div>}
          <ContentLibraryTable
            canCreate={canManage && categories.length > 0 && selectedCategory !== undefined && !query && !language && !status}
            createLabel="Создать статью"
            emptyDescription={articles.length === 0 && selectedCategory !== undefined ? "Создайте статью в этом разделе или переместите существующую." : undefined}
            emptyTitle={articles.length ? "Ничего не найдено" : "Материалов пока нет"}
            error={false}
            errorTitle="Не удалось загрузить материалы"
            hasItems={filtered.length > 0}
            loading={false}
            onCreate={() => setEditing(null)}
            onRetry={() => void reload()}
            footer={<div className="ai-table-footer"><span>{pluralRu(filtered.length, ["материал", "материала", "материалов"])}</span></div>}
          >
            <PortalArticleTable
              articles={filtered}
              canManage={canManage}
              canSelect={canLinkAgents}
              selectedIds={selectedIds}
              onArchive={(article) => setDecision({ article, type: "archive" })}
              onEdit={setEditing}
              onToggleSelected={toggleSelected}
              onToggleVisible={toggleVisible}
            />
          </ContentLibraryTable>
          {bulkMode && <p className="knowledge-bulk-note">Агент отвечает только по опубликованным статьям: черновики и архив в выдачу не попадают.</p>}
        </main>
      </div>
      {agentOpen && (
        <AgentLinkDialog
          agents={agentLinkOptions(agents)}
          busy={busy}
          error={agentError}
          forms={ARTICLE_FORMS}
          outcome={outcome}
          title="Статьи агента поддержки"
          onCancel={() => { setAgentOpen(false); if (outcome) setSelectedIds(new Set()); }}
          onSubmit={(agentId, action) => void submitAgentLink(agentId, action)}
        />
      )}
      {managingCategories && <PortalCategoryManagement categories={categories} portalId={portalId} onChanged={reload} onClose={() => setManagingCategories(false)} />}
      {importOpen && (
        <PortalArticleImportModal
          portalId={portalId}
          onClose={() => setImportOpen(false)}
          onImported={() => void reload()}
        />
      )}
      <DecisionDialog
        open={Boolean(decision)}
        onClose={() => setDecision(null)}
        tone={decision?.type === "archive" ? "danger" : "warning"}
        icon={decision?.type === "archive" ? "trash" : "check"}
        title={decision?.type === "archive" ? "Перенести статью в архив?" : "Опубликовать выбранную версию?"}
        description={decision?.type === "archive" ? "Статья исчезнет с публичного портала." : "Эта версия станет доступна посетителям портала."}
        actions={<><Button variant="secondary" onClick={() => setDecision(null)}>Отмена</Button><Button variant={decision?.type === "archive" ? "danger-outline" : "primary"} disabled={busy} onClick={() => void applyDecision()}>{decision?.type === "archive" ? "В архив" : "Опубликовать"}</Button></>}
      />
    </>
  );
}
