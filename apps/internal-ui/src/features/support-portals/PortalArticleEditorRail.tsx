import { Icon } from "../../shared/icons";
import { SelectField, TextAreaField } from "../../shared/form-controls";
import { shortDateTime } from "../../shared/utils";
import { t } from "../../i18n";
import { LOCALE_OPTIONS } from "./portalText";
import { PortalArticleFiles } from "./PortalArticleFiles";
import type { PortalArticleEditorState } from "./usePortalArticleEditor";

export function PortalArticleEditorRail({ state, canManage }: { state: PortalArticleEditorState; canManage: boolean }) {
  const { categoryId, category, setCategoryId, locale, setLocale, summary, setSummary,
    loaded, revisions, publishedRevisionId, selectedRevisionId, selectRevision } = state;
  const categoryOptions: Array<[string, string]> = state.categories.map(item => [String(item.id), item.name]);
  if (!state.categories.some(item => item.isSystem)) {
    categoryOptions.unshift(category?.isSystem ? [String(category.id), category.name] : ["", t("portals.uncategorized")]);
  }
  return (
    <aside className="portal-editor-rail">
      <div className="portal-rail-fields">
        <SelectField
          label={t("admin.section")}
          value={categoryId}
          onChange={setCategoryId}
          options={categoryOptions}
        />
        <SelectField
          label={t("portals.language")}
          value={locale}
          onChange={setLocale}
          options={LOCALE_OPTIONS.map(([value, label]) => [value, label])}
        />
        <div>
          <TextAreaField label={t("ai.short_description")} value={summary} onChange={setSummary} />
          <small className="portal-rail-hint">{t("portals.shown_list_search")}</small>
        </div>
      </div>

      <PortalArticleFiles state={state} canManage={canManage} />

      {loaded && (
        <div className="portal-rail-block">
          <div className="portal-rail-head">
            <span>{t("portals.reader_ratings")}</span>
          </div>
          <div className="portal-rail-votes">
            <span className="is-helpful">
              <Icon name="check" size={13} strokeWidth={2.4} />
              {loaded.feedback?.helpful ?? 0}
              <small>{t("portals.helpful")}</small>
            </span>
            <span className="is-unhelpful">
              <Icon name="close" size={13} strokeWidth={2.4} />
              {loaded.feedback?.unhelpful ?? 0}
              <small>{t("portals.did_not_help")}</small>
            </span>
          </div>
        </div>
      )}

      <div className="portal-rail-block">
        <div className="portal-rail-head">
          <span>{t("portals.versions")}</span>
          <span className="portal-rail-hint">{t("portals.immutable")}</span>
        </div>
        <div className="portal-rail-revisions">
          {revisions.map((revision) => {
            const published = revision.id === publishedRevisionId;
            return (
              <button
                className={`portal-rail-revision${revision.id === selectedRevisionId ? " is-current" : ""}`}
                key={revision.id}
                type="button"
                onClick={() => selectRevision(revision.id)}
              >
                <i className={published ? "is-published" : revision.id === selectedRevisionId ? "is-draft" : ""} />
                <span>
                  <strong>{t("portals.revision_number", { revision: revision.revision })}</strong>
                  <small>{published ? "" : t("portals.draft_prefix")}{shortDateTime(revision.createdAt)}{revision.authorName ? ` · ${revision.authorName}` : ""}</small>
                </span>
                {revision.id === selectedRevisionId && !published && <small className="portal-rail-tag is-current">{t("profile.current")}</small>}
                {published && <small className="portal-rail-tag is-published">{t("portals.published_2")}</small>}
              </button>
            );
          })}
        </div>
        <p>{t("portals.publishing_picks_one_revision_visitors")}</p>
      </div>
    </aside>
  );
}
