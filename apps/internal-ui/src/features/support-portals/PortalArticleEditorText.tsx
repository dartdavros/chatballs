import { Icon } from "../../shared/icons";
import { FormField } from "../../shared/form-controls";
import { applyMarkdownTool, cursorPosition, editorStats } from "../../shared/markdown/markdownTools";
import { fmt, t } from "../../i18n";
import { MARKDOWN_TOOLS } from "./markdownTools";
import type { PortalArticleEditorState } from "./usePortalArticleEditor";

export function PortalArticleEditorText({ state }: { state: PortalArticleEditorState }) {
  const { title, setTitle, editingSlug, setEditingSlug, slug, setSlug, loaded, imageInputRef, fileInputRef,
    textRef, applyEdit, content, setContent, setDropping, upload, setCaret, dropping, caret, autoSavedAt } = state;
  return (
    <div className="portal-editor-column">
      <div className="portal-editor-title">
        <FormField label={t("portals.article_title")} value={title} onChange={setTitle} />
        <div className="portal-editor-slug">
          <span>{t("portals.address")}</span>
          {editingSlug
            ? <input
                autoFocus
                value={slug}
                onBlur={() => loaded && setEditingSlug(false)}
                onChange={(event) => setSlug(event.target.value.toLocaleLowerCase())}
              />
            : <code>/articles/{slug}</code>}
          {!editingSlug && <button type="button" onClick={() => setEditingSlug(true)}>{t("portals.change")}</button>}
        </div>
      </div>

      <div className="portal-md-toolbar">
        {MARKDOWN_TOOLS.map((tool) => (tool.divider
          ? <i className="portal-md-divider" key={tool.key} />
          : (
            <button
              className={tool.accent ? "is-accent" : ""}
              key={tool.key}
              title={tool.title}
              type="button"
              onClick={() => {
                if (tool.key === "image") {
                  imageInputRef.current?.click();
                  return;
                }
                if (tool.key === "attach") {
                  fileInputRef.current?.click();
                  return;
                }
                const field = textRef.current;
                applyEdit(applyMarkdownTool(
                  tool.key,
                  content,
                  field?.selectionStart ?? content.length,
                  field?.selectionEnd ?? content.length,
                ));
              }}
            >
              {tool.text && <span>{tool.text}</span>}
              {tool.icon && <Icon name={tool.icon} size={15} strokeWidth={1.9} />}
            </button>
          )))}
        <span className="portal-editor-gap" />
        <span className="portal-md-format">GFM</span>
      </div>

      <div
        className="portal-editor-text"
        onDragEnter={(event) => { event.preventDefault(); setDropping(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { if (event.currentTarget === event.target) setDropping(false); }}
        onDrop={(event) => {
          event.preventDefault();
          setDropping(false);
          if (event.dataTransfer.files.length) void upload(event.dataTransfer.files, true);
        }}
      >
        <textarea
          ref={textRef}
          aria-label={t("ai.text")}
          placeholder={t("ai.text")}
          spellCheck
          value={content}
          onChange={(event) => { setContent(event.target.value); setCaret(event.target.selectionStart); }}
          onKeyUp={(event) => setCaret(event.currentTarget.selectionStart)}
          onClick={(event) => setCaret(event.currentTarget.selectionStart)}
        />
        {dropping && (
          <div className="portal-editor-drop">
            <Icon name="upload" size={30} strokeWidth={1.8} />
            <strong>{t("portals.drop_add_article")}</strong>
            <span>{t("portals.image_goes_into_text_other")}</span>
          </div>
        )}
      </div>

      <div className="portal-editor-status">
        <span>{editorStats(content)}</span>
        <span>{cursorPosition(content, caret)}</span>
        <span className="portal-editor-gap" />
        {autoSavedAt && <span>{t("portals.draft_autosaved_at", { time: fmt.time(autoSavedAt) })}</span>}
      </div>
    </div>
  );
}
