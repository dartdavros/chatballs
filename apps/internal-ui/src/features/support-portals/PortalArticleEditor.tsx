import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import { MarkdownContent } from "../help-center/MarkdownContent";
import { resolvePortalTheme } from "../help-center/themes/registry";
import {
  addArticleRevision,
  createPortalArticle,
  deleteArticleFile,
  loadPortalArticle,
  portalErrorMessage,
  updatePortalArticle,
  uploadArticleFile,
  type PortalArticle,
  type PortalArticleFile,
  type PortalCategory,
  type SupportPortal,
} from "./model";
import {
  applyMarkdownTool,
  cursorPosition,
  editorStats,
  fileMarkdown,
  fileMeta,
  isImageFile,
} from "../../shared/markdown/markdownTools";
import { MARKDOWN_TOOLS } from "./markdownTools";
import { LOCALE_OPTIONS } from "./portalText";
import { fmt, t } from "../../i18n";

// Редактор статьи (дизайн-базлайн v2, кадры PT7/PT8): полноэкранный split —
// слева текст с панелью Markdown, в центре живой предпросмотр в теме портала,
// справа рейка с разделом, файлами и версиями. Модалок нет.

type Mode = "edit" | "split" | "view";

type UploadingFile = { name: string; percent: number };

const MODES: Array<[Mode, string, "edit" | "split" | "eye", string]> = [
  ["edit", t("ai.text"), "edit", t("ai.editor_only")],
  ["split", t("ai.side_by_side"), "split", t("ai.text_preview")],
  ["view", t("ai.preview"), "eye", t("ai.preview_only")],
];

function draftKey(portalId: number, articleId: number | null): string {
  return `chatballs:portal-article-draft:${portalId}:${articleId ?? "new"}`;
}

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
  const portalId = portal.id;
  const [loaded, setLoaded] = useState<PortalArticle | null>(article);
  const [mode, setMode] = useState<Mode>("split");
  const [categoryId, setCategoryId] = useState(String(article?.category.id ?? categories[0]?.id ?? ""));
  const [locale, setLocale] = useState(article?.locale ?? portal.defaultLocale);
  const [slug, setSlug] = useState(article?.slug ?? "");
  const [editingSlug, setEditingSlug] = useState(!article);
  const [selectedRevisionId, setSelectedRevisionId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [caret, setCaret] = useState(0);
  const [files, setFiles] = useState<PortalArticleFile[]>([]);
  const [uploading, setUploading] = useState<UploadingFile | null>(null);
  const [dropping, setDropping] = useState(false);
  const [railDropping, setRailDropping] = useState(false);
  const [autoSavedAt, setAutoSavedAt] = useState<Date | null>(null);
  // Снимок последней сохранённой редакции: по нему видно, есть ли правки,
  // которых ещё нет ни в одной редакции — и, значит, нет на портале.
  const [baseline, setBaseline] = useState<{ title: string; summary: string; content: string } | null>(null);
  const [busy, setBusy] = useState(Boolean(article));
  const [error, setError] = useState("");
  const textRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!article) return;
    setBusy(true);
    loadPortalArticle(portalId, article.id)
      .then(({ article: detail }) => {
        setLoaded(detail);
        setFiles(detail.files ?? []);
        const revision = detail.revisions?.[0] ?? detail.publishedRevision;
        setSelectedRevisionId(revision?.id ?? null);
        setTitle(revision?.title ?? "");
        setSummary(revision?.summary ?? "");
        // Локальный автосейв поднимается поверх последней редакции: он новее.
        const draft = window.localStorage.getItem(draftKey(portalId, detail.id));
        setContent(draft ?? revision?.content ?? "");
        setBaseline({
          title: revision?.title ?? "",
          summary: revision?.summary ?? "",
          content: revision?.content ?? "",
        });
      })
      .catch((caught) => setError(portalErrorMessage(caught, t("portals.could_not_load_article"))))
      .finally(() => setBusy(false));
  }, [article, portalId]);

  // Автосохранение черновика в браузере: статусная строка показывает время.
  useEffect(() => {
    if (!content) return undefined;
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(draftKey(portalId, loaded?.id ?? null), content);
        setAutoSavedAt(new Date());
      } catch {
        // Приватный режим браузера: автосейв просто недоступен.
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [content, loaded?.id, portalId]);

  const revisions = useMemo(() => loaded?.revisions ?? [], [loaded]);
  const latestRevision = revisions[0] ?? null;
  const publishedRevisionId = loaded?.publishedRevision?.id ?? null;
  const category = categories.find((item) => item.id === Number(categoryId));
  const theme = resolvePortalTheme(portal.theme);

  function selectRevision(revisionId: number) {
    const revision = revisions.find((item) => item.id === revisionId);
    if (!revision) return;
    setSelectedRevisionId(revision.id);
    setTitle(revision.title);
    setSummary(revision.summary);
    setContent(revision.content);
    setBaseline({ title: revision.title, summary: revision.summary, content: revision.content });
  }

  function applyEdit(next: { value: string; selectionStart: number; selectionEnd: number }) {
    setContent(next.value);
    window.requestAnimationFrame(() => {
      const field = textRef.current;
      if (!field) return;
      field.focus();
      field.setSelectionRange(next.selectionStart, next.selectionEnd);
      setCaret(next.selectionStart);
    });
  }

  function insertText(snippet: string) {
    const field = textRef.current;
    const start = field?.selectionStart ?? content.length;
    const end = field?.selectionEnd ?? content.length;
    applyEdit({
      value: `${content.slice(0, start)}${snippet}${content.slice(end)}`,
      selectionStart: start + snippet.length,
      selectionEnd: start + snippet.length,
    });
  }

  const upload = useCallback(async (list: FileList | File[], insert: boolean) => {
    if (!loaded) {
      setError(t("portals.create_article_first_files_attach"));
      return;
    }
    setError("");
    for (const file of Array.from(list)) {
      setUploading({ name: file.name, percent: 0 });
      try {
        const payload = await uploadArticleFile(portalId, loaded.id, file, (percent) => {
          setUploading({ name: file.name, percent });
        });
        setFiles((current) => [payload.file, ...current.filter((item) => item.id !== payload.file.id)]);
        // Вставляем в текст только по явной команде «изображение»: файл,
        // прикреплённый к статье, в текст не лезет — он вложение.
        if (insert && isImageFile(payload.file.contentType, payload.file.name)) {
          insertText(`\n${fileMarkdown(payload.file.name, payload.file.path, true)}\n`);
        }
      } catch (caught) {
        setError(portalErrorMessage(caught, t("portals.could_not_upload_file", { name: file.name })));
      } finally {
        setUploading(null);
      }
    }
    // content нужен в зависимостях: вставка файла дописывает текущий текст.
  }, [loaded, portalId, content]);

  async function removeFile(file: PortalArticleFile) {
    try {
      if (loaded) await deleteArticleFile(portalId, loaded.id, file.id);
      setFiles((current) => current.filter((item) => item.id !== file.id));
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_delete_file")));
    }
  }

  async function save(): Promise<{ article: PortalArticle; revisionId: number } | null> {
    setBusy(true);
    setError("");
    try {
      if (loaded) {
        await updatePortalArticle(portalId, loaded.id, {
          categoryId: Number(categoryId),
          locale,
          slug,
        });
        const payload = await addArticleRevision(portalId, loaded.id, { title, summary, content });
        const detail = await loadPortalArticle(portalId, loaded.id);
        setLoaded(detail.article);
        setFiles(detail.article.files ?? []);
        setSelectedRevisionId(payload.revision.id);
        window.localStorage.removeItem(draftKey(portalId, loaded.id));
        // Бэкенд приводит ссылки на файлы к относительным — снимок и текст
        // берутся из сохранённой редакции, иначе экран сразу считался бы
        // изменённым.
        setContent(payload.revision.content);
        setBaseline({
          title: payload.revision.title,
          summary: payload.revision.summary,
          content: payload.revision.content,
        });
        await onSaved();
        return { article: detail.article, revisionId: payload.revision.id };
      } else {
        const created = await createPortalArticle(portalId, {
          categoryId: Number(categoryId),
          slug,
          locale,
          title,
          summary,
          content,
        });
        window.localStorage.removeItem(draftKey(portalId, null));
        setLoaded(created.article);
        const createdRevisionId = created.article.revisions?.[0]?.id ?? null;
        setSelectedRevisionId(createdRevisionId);
        setEditingSlug(false);
        const createdRevision = created.article.revisions?.[0];
        if (createdRevision) {
          setContent(createdRevision.content);
          setBaseline({
            title: createdRevision.title,
            summary: createdRevision.summary,
            content: createdRevision.content,
          });
        }
        await onSaved();
        return createdRevisionId === null ? null : { article: created.article, revisionId: createdRevisionId };
      }
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_save_article")));
      return null;
    } finally {
      setBusy(false);
    }
  }

  // «Опубликовать» публикует то, что человек видит на экране: несохранённый
  // текст сначала становится новой редакцией, иначе публиковалась бы старая
  // и правка молча пропадала бы.
  async function publish() {
    if (!loaded) {
      const created = await save();
      if (created) onPublish(created.article, created.revisionId);
      return;
    }
    // Сверяемся с сервером, а не с состоянием экрана: публикуется ровно то,
    // что человек видит. Совпало с последней редакцией — публикуем её,
    // иначе сначала сохраняем правки новой редакцией.
    const latest = await loadPortalArticle(portalId, loaded.id)
      .then(({ article: detail }) => detail.revisions?.[0] ?? null)
      .catch(() => null);
    if (latest && latest.title === title && latest.summary === summary && latest.content === content) {
      onPublish(loaded, latest.id);
      return;
    }
    const saved = await save();
    if (saved) onPublish(saved.article, saved.revisionId);
  }

  const ready = Boolean(title.trim() && content.trim() && categoryId && slug.trim());
  const draftPending = latestRevision !== null && latestRevision.id !== publishedRevisionId;
  // Правки живут в браузере, пока не создана редакция: на портале их нет.
  const dirty = baseline !== null
    && (baseline.title !== title || baseline.summary !== summary || baseline.content !== content);
  const badge = loaded === null
    ? { tone: "draft", text: t("portals.new_article_not_saved") }
    : dirty
      ? { tone: "draft", text: t("portals.there_unsaved_edits_they_not") }
      : draftPending
        ? { tone: "draft", text: t("portals.revision_draft", { revision: latestRevision!.revision }) }
        : { tone: "live", text: t("portals.revision_published", { revision: loaded.publishedRevision?.revision ?? "—" }) };

  return (
    <div className="portal-editor">
      <div className="portal-editor-head">
        <button className="portal-editor-back" type="button" onClick={onClose}>
          <Icon name="chevronLeft" size={16} strokeWidth={2} />{t("portals.material")}</button>
        <span className="portal-editor-crumb">{category?.name ?? ""}</span>
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
        {mode !== "view" && (
          <div className="portal-editor-column">
            <div className="portal-editor-title">
              <input
                placeholder={t("portals.article_title")}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
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
        )}

        {mode !== "edit" && (
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
                  <span>{t("portals.help")}</span><span>/</span><span>{category?.name ?? ""}</span>
                </div>
                <h1>{title || t("ai.untitled")}</h1>
                {summary && <p className="portal-preview-lead">{summary}</p>}
                <MarkdownContent content={content} />
              </article>
            </div>
          </div>
        )}

        <aside className="portal-editor-rail">
          <div className="portal-rail-fields">
            <label>
              <span>{t("admin.section")}</span>
              <span className="portal-select">
                <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                  {categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
                <Icon name="chevron" size={13} strokeWidth={2} />
              </span>
            </label>
            <label>
              <span>{t("portals.language")}</span>
              <span className="portal-select">
                <select value={locale} onChange={(event) => setLocale(event.target.value)}>
                  {LOCALE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <Icon name="chevron" size={13} strokeWidth={2} />
              </span>
            </label>
            <label>
              <span>{t("ai.short_description")}<small>{t("portals.shown_list_search")}</small></span>
              <textarea value={summary} onChange={(event) => setSummary(event.target.value)} />
            </label>
          </div>

          <div className="portal-rail-block">
            <div className="portal-rail-head">
              <span>{t("portals.article_files")}</span>
              <button type="button" onClick={() => fileInputRef.current?.click()}>{t("common.upload")}</button>
            </div>
            {/* Два механизма и два поля выбора: скрепка и рейка прикрепляют
                файл к статье, кнопка «изображение» ставит картинку в текст. */}
            <input
              ref={fileInputRef}
              hidden
              multiple
              type="file"
              onChange={(event) => {
                if (event.target.files?.length) void upload(event.target.files, false);
                event.target.value = "";
              }}
            />
            <input
              ref={imageInputRef}
              hidden
              multiple
              accept="image/*"
              type="file"
              onChange={(event) => {
                if (event.target.files?.length) void upload(event.target.files, true);
                event.target.value = "";
              }}
            />
            <div
              className={`portal-rail-drop${railDropping ? " is-hot" : ""}`}
              onDragEnter={(event) => { event.preventDefault(); setRailDropping(true); }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setRailDropping(false)}
              onDrop={(event) => {
                event.preventDefault();
                setRailDropping(false);
                if (event.dataTransfer.files.length) void upload(event.dataTransfer.files, false);
              }}
            >
              <Icon name="upload" size={20} strokeWidth={1.8} />
              <p>{t("ai.drag_files_here")}</p>
              <p>{t("ai.or")}<button type="button" onClick={() => fileInputRef.current?.click()}>{t("ai.pick_them_from_disk")}</button>{t("ai.up_25_mb")}</p>
            </div>

            <div className="portal-rail-files">
              {uploading && (
                <div className="portal-rail-file is-fresh">
                  <i><Icon name="image" size={14} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{uploading.name}</strong>
                    <small className="is-progress">{t("common.uploading_percent", { percent: uploading.percent })}</small>
                    <span className="portal-rail-progress"><i style={{ width: `${uploading.percent}%` }} /></span>
                  </span>
                </div>
              )}
              {files.map((file) => {
                const image = isImageFile(file.contentType, file.name);
                const inserted = content.includes(file.path) || content.includes(file.url);
                return (
                  <div className="portal-rail-file" key={file.id}>
                    <i><Icon name={image ? "image" : "file"} size={14} strokeWidth={1.8} /></i>
                    <span>
                      <strong>{file.name}</strong>
                      <small>{fileMeta(file.name, file.size)}{inserted ? ` ${t("portals.inserted_into_text")}` : ` ${t("portals.article_attachment")}`}</small>
                    </span>
                    {/* В текст вставляется только картинка: документ — вложение
                        статьи, посетитель скачивает его списком под текстом. */}
                    {image && !inserted && (
                      <button
                        className="portal-rail-file-insert"
                        title={t("portals.insert_into_text")}
                        type="button"
                        onClick={() => insertText(`\n${fileMarkdown(file.name, file.path, true)}\n`)}
                      >
                        <Icon name="plus" size={14} strokeWidth={2} />
                      </button>
                    )}
                    <button
                      title={t("ai.copy_as_markdown")}
                      type="button"
                      onClick={() => void navigator.clipboard?.writeText(fileMarkdown(file.name, file.path, image))}
                    >
                      <Icon name="copy" size={13} strokeWidth={1.9} />
                    </button>
                    {canManage && (
                      <button className="portal-rail-file-remove" title={t("portals.delete_file")} type="button" onClick={() => void removeFile(file)}>
                        <Icon name="trash" size={13} strokeWidth={1.9} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

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
      </div>
    </div>
  );
}
