import { Dropdown } from "antd";
import { useMemo, useState } from "react";

import { CategoryTree } from "../../shared/content-library/CategoryTree";
import { ContentLibraryTable } from "../../shared/content-library/ContentLibraryTable";
import { ContentLibraryToolbar } from "../../shared/content-library/ContentLibraryToolbar";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { formatDate } from "../../shared/utils";
import { PortalArticleEditor } from "./PortalArticleEditor";
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

export function PortalContent({
  articles,
  canManage,
  categories,
  locale,
  portalId,
  reload,
}: {
  articles: PortalArticle[];
  canManage: boolean;
  categories: PortalCategory[];
  locale: string;
  portalId: number;
  reload: () => Promise<void>;
}) {
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [status, setStatus] = useState("");
  const [editing, setEditing] = useState<PortalArticle | null | undefined>(undefined);
  const [managingCategories, setManagingCategories] = useState(false);
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
          <ContentLibraryToolbar
            query={query}
            onQueryChange={setQuery}
            action={canManage && categories.length > 0 && <Button variant="primary" icon="plus" onClick={() => setEditing(null)}>Новая статья</Button>}
          >
            <label className="knowledge-filter-select"><span>Язык:</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">Все</option><option value="ru">Русский</option><option value="en">English</option></select></label>
            <label className="knowledge-filter-select"><span>Статус:</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Все</option><option value="DRAFT">Черновик</option><option value="PUBLISHED">Опубликована</option><option value="ARCHIVED">Архив</option></select></label>
          </ContentLibraryToolbar>
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
            footer={<div className="ai-table-footer"><span>{filtered.length} материалов</span></div>}
          >
              <table className="baseline-table knowledge-table">
                <thead><tr><th>СТАТЬЯ</th><th>РАЗДЕЛ</th><th>ЯЗЫК</th><th>ВЕРСИЯ</th><th>СТАТУС</th><th>ОБНОВЛЕНО</th><th /></tr></thead>
                <tbody>
                  {filtered.map((article) => (
                    <tr className="knowledge-row" key={article.id} onClick={() => setEditing(article)}>
                      <td><button className="link is-strong is-neutral" type="button" onClick={() => setEditing(article)}>{article.latestRevision?.title || article.slug}</button><small className="knowledge-description">{article.latestRevision?.summary || article.slug}</small></td>
                      <td className="knowledge-category-path">{article.category.name}</td>
                      <td>{article.locale.toLocaleUpperCase()}</td>
                      <td>{article.publishedRevision ? article.publishedRevision.revision : "—"}</td>
                      <td><StatusPill status={article.status === "PUBLISHED" ? "published" : article.status === "ARCHIVED" ? "archived" : "draft"} /></td>
                      <td>{formatDate(article.updatedAt)}</td>
                      <td onClick={(event) => event.stopPropagation()}>
                        {canManage && (
                          <Dropdown
                            overlayClassName="app-dropdown"
                            trigger={["click"]}
                            menu={{ items: [
                              { key: "edit", label: "Изменить", onClick: () => setEditing(article) },
                              ...(article.status !== "ARCHIVED" ? [{ key: "archive", danger: true, label: "В архив", onClick: () => setDecision({ article, type: "archive" as const }) }] : []),
                            ] }}
                          >
                            <button aria-label={`Действия: ${article.latestRevision?.title ?? article.slug}`} className="row-menu-button" type="button"><Icon name="more" size={18} /></button>
                          </Dropdown>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
          </ContentLibraryTable>
        </main>
      </div>
      {managingCategories && <PortalCategoryManagement categories={categories} portalId={portalId} onChanged={reload} onClose={() => setManagingCategories(false)} />}
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
