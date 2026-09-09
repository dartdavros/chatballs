import { Dropdown } from "antd";
import { useCallback, useMemo, useState } from "react";

import {
  AgentLinkDialog,
  type AgentLinkAction,
  type AgentLinkOutcome,
} from "../../shared/content-library/AgentLinkDialog";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { Button, FilterDropdown, SearchInput } from "../../shared/ui-controls";
import { agentLinkOptions } from "../ai/agentOptions";
import { linkPortalArticlesToAgent } from "../ai/knowledge/model";
import { Pagination } from "../../shared/Pagination";
import { useDebounced } from "../../shared/useDebounced";
import { usePagedResource } from "../../shared/usePagedResource";
import { useAiAgents } from "../ai/useAiAgents";
import {
  archivePortalArticle,
  listPortalArticles,
  portalErrorMessage,
  ARTICLE_STATUS_LABEL,
  type ArticleStatus,
  type PortalArticle,
  type PortalCategory,
} from "./model";
import { PortalArticleImportModal } from "./PortalArticleImportModal";
import { PortalCategoryManagement } from "./PortalCategoryManagement";
import { LOCALE_OPTIONS, revisionSummary, updatedAt } from "./portalText";
import { t, tn } from "../../i18n";

// Библиотека материалов портала (дизайн-базлайн v2, кадр PT3): дерево разделов
// 260px с вложенностью и счётчиками, тулбар и таблица статей — без вкладок.


const STATUS_FILTER = [
  { value: "PUBLISHED", label: ARTICLE_STATUS_LABEL.PUBLISHED },
  { value: "DRAFT", label: ARTICLE_STATUS_LABEL.DRAFT },
  { value: "ARCHIVED", label: ARTICLE_STATUS_LABEL.ARCHIVED },
];

type SectionRow = { category: PortalCategory; depth: number; count: number };

function pillStatus(status: ArticleStatus): "published" | "archived" | "draft" {
  if (status === "PUBLISHED") return "published";
  if (status === "ARCHIVED") return "archived";
  return "draft";
}

/** Разделы в порядке дерева с отступом по глубине (кадр PT3, левая панель). */
function sectionRows(categories: PortalCategory[]): SectionRow[] {
  const byParent = new Map<number | null, PortalCategory[]>();
  categories.forEach((category) => {
    const siblings = byParent.get(category.parentId) ?? [];
    siblings.push(category);
    byParent.set(category.parentId, siblings);
  });
  byParent.forEach((items) => items.sort((left, right) => (
    left.sortOrder - right.sortOrder || left.name.localeCompare(right.name, "ru")
  )));
  const rows: SectionRow[] = [];
  const walk = (parentId: number | null, depth: number) => {
    (byParent.get(parentId) ?? []).forEach((category) => {
      rows.push({ category, depth, count: category.articleCount });
      walk(category.id, depth + 1);
    });
  };
  walk(null, 0);
  return rows;
}

export function PortalLibrary({
  canLinkAgents,
  canManage,
  categories,
  portalId,
  reload,
  onEditArticle,
}: {
  canLinkAgents: boolean;
  canManage: boolean;
  categories: PortalCategory[];
  portalId: number;
  reload: () => Promise<void>;
  onEditArticle: (article: PortalArticle) => void;
}) {
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState<string[]>([]);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [status, setStatus] = useState<string[]>([]);
  const [statusOpen, setStatusOpen] = useState(false);
  const [managingCategories, setManagingCategories] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [linking, setLinking] = useState<PortalArticle | null>(null);
  const [linkOutcome, setLinkOutcome] = useState<AgentLinkOutcome | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState<PortalArticle | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { agents } = useAiAgents();

  const rows = useMemo(() => sectionRows(categories), [categories]);
  const total = categories
    .filter((category) => category.parentId === null)
    .reduce((sum, category) => sum + category.articleCount, 0);

  // Категория (вместе с вложенными), язык, статус, поиск и страница — запрос к
  // серверу: статей в библиотеке может быть сколько угодно.
  const settledQuery = useDebounced(query);
  const request = useMemo(
    () => ({ category: selectedCategory, locale: language, status, search: settledQuery }),
    [language, selectedCategory, settledQuery, status],
  );
  const loadArticles = useCallback(
    (page: number) => listPortalArticles(portalId, request, page),
    [portalId, request],
  );
  const articles = usePagedResource(loadArticles, request, t("portals.could_not_load_articles"));
  const reloadAll = useCallback(async () => {
    await Promise.all([reload(), articles.reload()]);
  }, [articles, reload]);

  async function submitAgentLink(agentId: number, action: AgentLinkAction) {
    if (!linking) return;
    setBusy(true);
    setLinkError(null);
    try {
      const result = await linkPortalArticlesToAgent({ agentId, action, articleIds: [linking.id] });
      setLinkOutcome({ action, changed: result.changed, skipped: result.skippedIds.length });
    } catch (caught) {
      setLinkError(portalErrorMessage(caught, t("portals.could_not_change_agent_s")));
    } finally {
      setBusy(false);
    }
  }

  async function archive() {
    if (!archiving) return;
    setBusy(true);
    setError("");
    try {
      await archivePortalArticle(portalId, archiving.id);
      setArchiving(null);
      await reloadAll();
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_change_article")));
      setArchiving(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-library">
      <aside className="portal-sections">
        <header>
          <span>{t("portals.sections")}</span>
          {canManage && <button type="button" onClick={() => setManagingCategories(true)}>{t("ai.manage")}</button>}
        </header>
        <nav>
          <button
            className={`portal-section-row${selectedCategory === undefined ? " is-active" : ""}`}
            style={{ paddingLeft: 9 }}
            type="button"
            onClick={() => { setSelectedCategory(undefined); }}
          >
            <Icon name="folder" size={15} strokeWidth={1.8} />
            <span>{t("portals.all_material")}</span>
            <small>{total}</small>
          </button>
          {rows.map(({ category, depth, count }) => (
            <button
              className={`portal-section-row${selectedCategory === category.id ? " is-active" : ""}`}
              key={category.id}
              style={{ paddingLeft: 9 + depth * 16 }}
              type="button"
              onClick={() => { setSelectedCategory(category.id); }}
            >
              <span>{category.name}</span>
              <small>{count}</small>
            </button>
          ))}
        </nav>
        {canManage && (
          <div className="portal-sections-foot">
            <button type="button" onClick={() => setManagingCategories(true)}>
              <Icon name="plus" size={14} strokeWidth={2} />{t("portals.add_section")}</button>
          </div>
        )}
      </aside>

      <div className="portal-library-main">
        <div className="portal-library-inner">
          <div className="portal-library-toolbar">
            <SearchInput
              className="portal-library-search"
              placeholder={t("portals.search_articles")}
              value={query}
              onChange={setQuery}
            />
            <FilterDropdown
              caption={t("portals.language_2")}
              label={language.length === 1 ? LOCALE_OPTIONS.find(([value]) => value === language[0])![1] : t("common.all")}
              multiple
              open={languageOpen}
              options={LOCALE_OPTIONS.map(([value, label]) => ({ value, label }))}
              selected={language}
              onOpenChange={setLanguageOpen}
              onSelect={(value) => {
                setLanguage((current) => (current.includes(value)
                  ? current.filter((item) => item !== value)
                  : [...current, value]));
              }}
            />
            <FilterDropdown
              caption={t("portals.status")}
              label={status.length === 1 ? STATUS_FILTER.find((item) => item.value === status[0])!.label : t("common.all")}
              multiple
              open={statusOpen}
              options={STATUS_FILTER}
              selected={status}
              onOpenChange={setStatusOpen}
              onSelect={(value) => {
                setStatus((current) => (current.includes(value)
                  ? current.filter((item) => item !== value)
                  : [...current, value]));
              }}
            />
            <span className="portal-library-toolbar-gap" />
            {canManage && (
              <Button variant="secondary" className="portal-import-button" icon="import" onClick={() => setImportOpen(true)}>{t("portals.article_import")}</Button>
            )}
          </div>

          {error && <div className="portal-form-error">{error}</div>}

          <table className="portal-articles-table">
            <thead>
              <tr>
                <th>{t("portals.article")}</th>
                <th>{t("portals.section")}</th>
                <th>{t("portals.language_3")}</th>
                <th>{t("portals.revision")}</th>
                <th>{t("portals.ratings")}</th>
                <th>{t("common.status_2")}</th>
                <th>{t("ai.updated_2")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {articles.items.map((article) => {
                const title = article.latestRevision?.title || article.slug;
                const { revision, note } = revisionSummary(article);
                const helpful = article.feedback?.helpful ?? 0;
                const unhelpful = article.feedback?.unhelpful ?? 0;
                const votes = { helpful, unhelpful, total: helpful + unhelpful };
                const menuItems = [
                  { key: "edit", label: <button type="button" onClick={() => onEditArticle(article)}><Icon name="edit" size={15} strokeWidth={1.9} />{t("common.edit")}</button> },
                  ...(canLinkAgents ? [{
                    key: "agent",
                    label: <button type="button" onClick={() => { setLinking(article); setLinkOutcome(null); setLinkError(null); }}><Icon name="robot" size={15} strokeWidth={1.9} />{t("ai.attach_agent")}</button>,
                  }] : []),
                  ...(canManage && article.status !== "ARCHIVED" ? [
                    { key: "divider", type: "divider" as const },
                    { key: "archive", label: <button className="danger" type="button" onClick={() => setArchiving(article)}><Icon name="trash" size={15} strokeWidth={1.9} />{t("common.archive")}</button> },
                  ] : []),
                ];
                return (
                  <tr
                    className={`portal-article-row${article.status === "ARCHIVED" ? " is-archived" : ""}`}
                    key={article.id}
                    onClick={() => onEditArticle(article)}
                  >
                    <td>
                      <span className="portal-article-name">
                        <i><Icon name="file" size={14} strokeWidth={1.8} /></i>
                        <span>
                          <strong>{title}</strong>
                          <small>/{article.slug}</small>
                        </span>
                        {article.fileCount > 0 && (
                          <small className="portal-article-files" title={t("portals.files_article")}>
                            <Icon name="attach" size={12} strokeWidth={1.9} />{article.fileCount}
                          </small>
                        )}
                      </span>
                    </td>
                    <td className="portal-article-category">{article.category.name}</td>
                    <td className="portal-article-locale">{article.locale.toLocaleUpperCase()}</td>
                    <td className="portal-article-revision">
                      <span>{revision}</span>
                      {note && <small>{note}</small>}
                    </td>
                    <td className="portal-article-votes">
                      {votes.total === 0 ? (
                        <span className="portal-votes-empty" title={t("portals.no_reader_ratings_yet")}>—</span>
                      ) : (
                        <span className="portal-votes" title={t("portals.votes_summary", { helpful: votes.helpful, unhelpful: votes.unhelpful })}>
                          <b className="is-up"><Icon name="thumbUp" size={13} strokeWidth={1.9} />{votes.helpful}</b>
                          <b className="is-down"><Icon name="thumbDown" size={13} strokeWidth={1.9} />{votes.unhelpful}</b>
                        </span>
                      )}
                    </td>
                    <td><StatusPill status={pillStatus(article.status)} label={ARTICLE_STATUS_LABEL[article.status]} /></td>
                    <td className="portal-article-updated">{updatedAt(article.updatedAt)}</td>
                    <td className="row-actions" onClick={(event) => event.stopPropagation()}>
                      <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-portal-menu" placement="bottomRight" trigger={["click"]}>
                        <button aria-label={t("common.actions_for", { name: title })} className="row-menu-button" type="button"><Icon name="more" size={16} strokeWidth={2} /></button>
                      </Dropdown>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <Pagination
            note={t("portals.library_note", { count: tn("plural.articles", articles.total), shown: articles.items.length })}
            page={articles.page}
            pageCount={articles.pageCount}
            onPage={articles.setPage}
          />
        </div>
      </div>

      {linking && (
        <AgentLinkDialog
          agents={agentLinkOptions(agents)}
          busy={busy}
          error={linkError}
          countKey="plural.articles"
          outcome={linkOutcome}
          title={t("portals.support_agent_articles")}
          onCancel={() => setLinking(null)}
          onSubmit={(agentId, action) => void submitAgentLink(agentId, action)}
        />
      )}
      {managingCategories && (
        <PortalCategoryManagement
          categories={categories}
          portalId={portalId}
          onChanged={reload}
          onClose={() => setManagingCategories(false)}
        />
      )}
      {importOpen && (
        <PortalArticleImportModal
          portalId={portalId}
          onClose={() => setImportOpen(false)}
          onImported={() => void reloadAll()}
        />
      )}
      <DecisionDialog
        open={archiving !== null}
        onClose={() => setArchiving(null)}
        tone="danger"
        icon="trash"
        title={t("portals.move_article_archive")}
        description={t("portals.article_will_disappear_from_public")}
        actions={<>
          <Button variant="secondary" onClick={() => setArchiving(null)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => void archive()}>{t("common.archive")}</Button>
        </>}
      />
    </div>
  );
}
