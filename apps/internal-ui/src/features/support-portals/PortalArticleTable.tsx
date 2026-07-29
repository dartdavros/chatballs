import { Dropdown } from "antd";

import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { formatDate } from "../../shared/utils";
import type { PortalArticle } from "./model";

export function PortalArticleTable({
  articles,
  canManage,
  onArchive,
  onEdit,
}: {
  articles: PortalArticle[];
  canManage: boolean;
  onArchive: (article: PortalArticle) => void;
  onEdit: (article: PortalArticle) => void;
}) {
  return (
    <table className="baseline-table knowledge-table portal-article-table">
      <colgroup>
        <col className="portal-article-col-title" />
        <col className="portal-article-col-category" />
        <col className="portal-article-col-language" />
        <col className="portal-article-col-version" />
        <col className="portal-article-col-status" />
        <col className="portal-article-col-updated" />
        <col className="portal-article-col-actions" />
      </colgroup>
      <thead><tr><th>СТАТЬЯ</th><th>РАЗДЕЛ</th><th>ЯЗЫК</th><th>ВЕРСИЯ</th><th>СТАТУС</th><th>ОБНОВЛЕНО</th><th /></tr></thead>
      <tbody>
        {articles.map((article) => {
          const title = article.latestRevision?.title || article.slug;
          const menuItems = [
            {
              key: "edit",
              label: <button type="button" onClick={() => onEdit(article)}><Icon name="edit" size={15} />Изменить</button>,
            },
            ...(article.status !== "ARCHIVED" ? [{
              key: "archive",
              label: <button className="danger" type="button" onClick={() => onArchive(article)}><Icon name="trash" size={15} />В архив</button>,
            }] : []),
          ];
          return (
            <tr className="knowledge-row" key={article.id} onClick={() => onEdit(article)}>
              <td>
                <button
                  className="link is-strong is-neutral"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onEdit(article);
                  }}
                >
                  {title}
                </button>
                <small className="knowledge-description">{article.latestRevision?.summary || article.slug}</small>
              </td>
              <td className="knowledge-category-path">{article.category.name}</td>
              <td>{article.locale.toLocaleUpperCase()}</td>
              <td>{article.publishedRevision ? article.publishedRevision.revision : "—"}</td>
              <td><StatusPill status={article.status === "PUBLISHED" ? "published" : article.status === "ARCHIVED" ? "archived" : "draft"} /></td>
              <td>{formatDate(article.updatedAt)}</td>
              <td className="row-actions" onClick={(event) => event.stopPropagation()}>
                {canManage && (
                  <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown" placement="bottomRight" trigger={["click"]}>
                    <button aria-label={`Действия: ${title}`} className="row-menu-button" type="button"><Icon name="more" size={18} /></button>
                  </Dropdown>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
