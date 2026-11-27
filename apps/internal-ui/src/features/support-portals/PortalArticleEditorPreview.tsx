import { Icon } from "../../shared/icons";
import { MarkdownContent } from "../help-center/MarkdownContent";
import { resolvePortalTheme } from "../help-center/themes/registry";
import { t } from "../../i18n";
import type { PortalArticleEditorState } from "./usePortalArticleEditor";

export function PortalArticleEditorPreview({ state }: { state: PortalArticleEditorState }) {
  const { category, portal, title, summary, content } = state;
  const theme = resolvePortalTheme(portal.theme);
  return (
    <div className="portal-preview-column">
      <div className="portal-preview-head">
        <span>{t("portals.preview_theme", { theme: theme.name.toLocaleUpperCase() })}</span>
        <span className="portal-editor-gap" />
        <a href={portal.publicUrl} rel="noreferrer" target="_blank" title={t("portals.open_as_visitor")}>
          <Icon name="external" size={13} strokeWidth={1.9} />{t("portals.visitor_s_view")}</a>
      </div>
      <div className="portal-preview-body">
        <article className="portal-preview-article">
          <div className="portal-preview-crumbs">
            <span>{t("portals.help")}</span><span>/</span><span>{category?.name ?? t("portals.uncategorized")}</span>
          </div>
          <h1>{title || t("ai.untitled")}</h1>
          {summary && <p className="portal-preview-lead">{summary}</p>}
          <MarkdownContent content={content} />
        </article>
      </div>
    </div>
  );
}
