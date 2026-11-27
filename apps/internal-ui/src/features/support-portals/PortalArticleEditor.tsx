import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";
import type { PortalArticle, PortalCategory, SupportPortal } from "./model";
import { PortalArticleEditorText } from "./PortalArticleEditorText";
import { PortalArticleEditorRail } from "./PortalArticleEditorRail";
import { PortalArticleEditorPreview } from "./PortalArticleEditorPreview";
import { usePortalArticleEditor } from "./usePortalArticleEditor";

type Mode = "edit" | "split" | "view";
const MODES: Array<[Mode, string, "edit" | "split" | "eye", string]> = [
  ["edit", t("ai.text"), "edit", t("ai.editor_only")],
  ["split", t("ai.side_by_side"), "split", t("ai.text_preview")],
  ["view", t("ai.preview"), "eye", t("ai.preview_only")],
];

export function PortalArticleEditor({
  article,
  canManage,
  categories,
  portal,
  onClose,
  onPublish,
  onSaved,
}: {
  article: PortalArticle | null;
  canManage: boolean;
  categories: PortalCategory[];
  portal: SupportPortal;
  onClose: () => void;
  onPublish: (article: PortalArticle, revisionId: number) => void;
  onSaved: () => Promise<void>;
}) {
  const state = usePortalArticleEditor({ article, categories, portal, onPublish, onSaved });
  const { category, mode, setMode, busy, ready, save, publish, badge, error } = state;
  return (
    <div className="portal-editor">
      <div className="portal-editor-head">
        <button className="portal-editor-back" type="button" onClick={onClose}>
          <Icon name="chevronLeft" size={16} strokeWidth={2} />{t("portals.material")}</button>
        <span className="portal-editor-crumb">{category?.name ?? t("portals.uncategorized")}</span>
        <span className="portal-editor-gap" />
        <span className={`portal-editor-badge is-${badge.tone}`}><i />{badge.text}</span>
        <Segmented className="portal-editor-modes" items={MODES} value={mode} setValue={setMode} />
        {canManage && (
          <Button variant="secondary" className="portal-editor-save" disabled={busy || !ready} onClick={() => void save()}>{t("portals.save_draft")}</Button>
        )}
        {canManage && (
          <Button
            variant="primary"
            className="portal-editor-publish"
            icon="check"
            disabled={busy || !ready}
            onClick={() => void publish()}
          >{t("common.publish")}</Button>
        )}
      </div>

      {error && <div className="portal-form-error portal-editor-error">{error}</div>}
      <div className="portal-editor-body">
        {mode !== "view" && <PortalArticleEditorText state={state} />}
        {mode !== "edit" && <PortalArticleEditorPreview state={state} />}
        <PortalArticleEditorRail state={state} canManage={canManage} />
      </div>
    </div>
  );
}
