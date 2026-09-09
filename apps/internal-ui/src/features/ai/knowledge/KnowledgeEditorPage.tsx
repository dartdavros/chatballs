import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../../shared/icons";
import {
  applyMarkdownTool,
  cursorPosition,
  type MarkdownTool,
} from "../../../shared/markdown/markdownTools";
import { EmptyState, LoadingState, Segmented } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { AgentRef } from "../../agents/model";
import { MarkdownContent } from "../../help-center/MarkdownContent";
import {
  agentStates,
  attachmentMarkdown,
  attachmentMeta,
  isImageAttachment,
  knowledgeChunks,
  knowledgeEditorStats,
} from "./knowledgeLibraryModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import {
  createKnowledgeItem,
  deleteAttachment,
  fetchKnowledgeItem,
  reindexKnowledge,
  updateKnowledgeItem,
  uploadAttachment,
  type KnowledgeAttachment,
  type KnowledgeItem,
} from "./model";
import { useKnowledgeCategories } from "./useKnowledgeCategories";
import { fmt, t, tn } from "../../../i18n";

// Редактор знания (дизайн-базлайн v2, кадры KB5/KB6): тот же полноэкранный
// split, что у статьи портала, — текст с панелью Markdown, предпросмотр и
// рейка 300px. Файл, брошенный в текст, становится вложением и ссылкой.

type Mode = "edit" | "split" | "view";

const MODES: Array<[Mode, string, "edit" | "split" | "eye", string]> = [
  ["edit", t("ai.text"), "edit", t("ai.editor_only")],
  ["split", t("ai.side_by_side"), "split", t("ai.text_preview")],
  ["view", t("ai.preview"), "eye", t("ai.preview_only")],
];

// Панель Markdown знания (кадр KB5): без кнопки «изображение» — любой файл
// прикрепляется к знанию и ставится в текст ссылкой.
const KNOWLEDGE_MARKDOWN_TOOLS: MarkdownTool[] = [
  { key: "h1", title: t("ai.heading_1"), text: "H1" },
  { key: "h2", title: t("ai.heading_2"), text: "H2" },
  { key: "divider-1", title: "", divider: true },
  { key: "bold", title: t("ai.bold"), icon: "bold" },
  { key: "italic", title: t("ai.italic"), icon: "italic" },
  { key: "link", title: t("ai.link"), icon: "link" },
  { key: "code", title: t("ai.code"), icon: "code" },
  { key: "divider-2", title: "", divider: true },
  { key: "list", title: t("ai.list"), icon: "list" },
  { key: "numlist", title: t("ai.numbered_list"), icon: "numlist" },
  { key: "quote", title: t("ai.quote"), icon: "quote" },
  { key: "table", title: t("ai.table"), icon: "table" },
  { key: "divider-3", title: "", divider: true },
  { key: "attach", title: t("common.attach_file"), icon: "attach", accent: true },
];

function draftKey(knowledgeId: number | null): string {
  return `chatballs:knowledge-draft:${knowledgeId ?? "new"}`;
}

type PendingFile = { name: string; percent: number };

export function KnowledgeEditorPage({
  agents,
  canManage,
  knowledgeId,
  openKnowledge,
  reloadAgents,
  setRoute,
}: {
  agents: AgentRef[];
  canManage: boolean;
  knowledgeId: number | null;
  openKnowledge: (knowledgeId: number) => void;
  reloadAgents: () => void;
  setRoute: (route: RouteKey) => void;
}) {
  const catalog = useKnowledgeCategories();
  const [loaded, setLoaded] = useState<KnowledgeItem | null>(null);
  const [mode, setMode] = useState<Mode>("split");
  const [asAgent, setAsAgent] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [isEnabled, setIsEnabled] = useState(true);
  const [attachments, setAttachments] = useState<KnowledgeAttachment[]>([]);
  const [queued, setQueued] = useState<File[]>([]);
  const [uploading, setUploading] = useState<PendingFile | null>(null);
  const [caret, setCaret] = useState(0);
  const [dropping, setDropping] = useState(false);
  const [railDropping, setRailDropping] = useState(false);
  const [autoSavedAt, setAutoSavedAt] = useState<Date | null>(null);
  const [baseline, setBaseline] = useState<{ title: string; description: string; content: string; isEnabled: boolean; categoryId: string } | null>(null);
  const [busy, setBusy] = useState(Boolean(knowledgeId));
  const [error, setError] = useState("");
  const textRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    if (!knowledgeId) return;
    setBusy(true);
    try {
      const { knowledge } = await fetchKnowledgeItem(knowledgeId);
      setLoaded(knowledge);
      setTitle(knowledge.title);
      setDescription(knowledge.description);
      setCategoryId(String(knowledge.category.id));
      setIsEnabled(knowledge.isEnabled);
      setAttachments(knowledge.attachments);
      const draft = window.localStorage.getItem(draftKey(knowledge.id));
      setContent(draft ?? knowledge.content ?? "");
      setBaseline({
        title: knowledge.title,
        description: knowledge.description,
        content: knowledge.content ?? "",
        isEnabled: knowledge.isEnabled,
        categoryId: String(knowledge.category.id),
      });
    } catch {
      setError(t("ai.could_not_load_knowledge_item"));
    } finally {
      setBusy(false);
    }
  }, [knowledgeId]);

  useEffect(() => { void load(); }, [load]);

  // Новое знание попадает в системную «Без категории», как и при импорте.
  useEffect(() => {
    if (knowledgeId || categoryId || catalog.categories.length === 0) return;
    const fallback = catalog.categories.find((category) => category.isSystem) ?? catalog.categories[0];
    setCategoryId(String(fallback.id));
  }, [catalog.categories, categoryId, knowledgeId]);

  // Автосохранение черновика в браузере: статусная строка показывает время.
  useEffect(() => {
    if (!content) return undefined;
    const timer = window.setTimeout(() => {
      try {
        window.localStorage.setItem(draftKey(loaded?.id ?? null), content);
        setAutoSavedAt(new Date());
      } catch {
        // Приватный режим браузера: автосейв просто недоступен.
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [content, loaded?.id]);

  const category = catalog.categories.find((item) => item.id === Number(categoryId)) ?? null;
  const categoryPath = category ? knowledgeCategoryPath(catalog.categories, category.id) : "";
  const attached = useMemo(() => agentStates(loaded?.agents ?? []), [loaded]);
  const dirty = baseline === null
    ? Boolean(title.trim() || content.trim())
    : baseline.title !== title
      || baseline.description !== description
      || baseline.content !== content
      || baseline.isEnabled !== isEnabled
      || baseline.categoryId !== categoryId;
  const ready = Boolean(title.trim() && categoryId);

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
    const files = Array.from(list);
    if (!loaded) {
      // Знание ещё не создано: файлы ждут сохранения и уходят следом за ним.
      setQueued((current) => [...current, ...files]);
      return;
    }
    setError("");
    for (const file of files) {
      setUploading({ name: file.name, percent: 0 });
      try {
        const { attachment } = await uploadAttachment(loaded.id, file);
        setAttachments((current) => [attachment, ...current.filter((item) => item.id !== attachment.id)]);
        if (insert) insertText(`\n${attachmentMarkdown(attachment)}\n`);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : t("ai.could_not_upload_file", { name: file.name }));
      } finally {
        setUploading(null);
      }
    }
    // content в зависимостях: вставка ссылки дописывает текущий текст.
  }, [content, loaded]);

  async function removeAttachment(attachment: KnowledgeAttachment) {
    if (!loaded) return;
    try {
      await deleteAttachment(loaded.id, attachment.id);
      setAttachments((current) => current.filter((item) => item.id !== attachment.id));
    } catch {
      setError(t("ai.could_not_delete_attachment"));
    }
  }

  async function save() {
    if (!ready) { setError(t("ai.give_title_category")); return; }
    setBusy(true);
    setError("");
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        content,
        categoryId: Number(categoryId),
        isEnabled,
      };
      if (loaded) {
        await updateKnowledgeItem(loaded.id, payload);
        window.localStorage.removeItem(draftKey(loaded.id));
        await load();
        reloadAgents();
      } else {
        const { knowledge } = await createKnowledgeItem(payload);
        for (const file of queued) await uploadAttachment(knowledge.id, file);
        setQueued([]);
        window.localStorage.removeItem(draftKey(null));
        reloadAgents();
        openKnowledge(knowledge.id);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("ai.could_not_save_knowledge_item"));
    } finally {
      setBusy(false);
    }
  }

  function revert() {
    if (!baseline) {
      setTitle("");
      setDescription("");
      setContent("");
      return;
    }
    setTitle(baseline.title);
    setDescription(baseline.description);
    setContent(baseline.content);
    setIsEnabled(baseline.isEnabled);
    setCategoryId(baseline.categoryId);
    window.localStorage.removeItem(draftKey(loaded?.id ?? null));
  }

  if (catalog.loading) return <div className="knowledge-editor"><LoadingState /></div>;
  if (catalog.error) return <div className="knowledge-editor"><EmptyState title={t("ai.could_not_load_categories")} /></div>;

  const chunks = knowledgeChunks(content);

  return (
    <div className="knowledge-editor">
      <div className="knowledge-editor-head">
        <button className="knowledge-editor-back" type="button" onClick={() => (loaded ? openKnowledge(loaded.id) : setRoute("knowledge"))}>
          <Icon name="chevronLeft" size={16} strokeWidth={2} />{t("common.knowledge_base")}</button>
        <span className="knowledge-editor-crumb">{categoryPath}</span>
        <span className="knowledge-editor-gap" />
        <span className={`knowledge-editor-badge${dirty ? " is-dirty" : ""}`}>
          <i />{dirty ? t("ai.there_unsaved_edits") : t("ai.index_up_date")}
        </span>
        <Segmented className="knowledge-editor-modes" items={MODES} value={mode} setValue={setMode} />
        {canManage && (
          <Button variant="secondary" className="knowledge-editor-revert" disabled={busy || !dirty} onClick={revert}>{t("ai.discard_edits")}</Button>
        )}
        {canManage && (
          <Button variant="primary" className="knowledge-editor-save" icon="check" disabled={busy || !ready} onClick={() => void save()}>{t("ai.save_reindex")}</Button>
        )}
      </div>

      {error && <div className="knowledge-form-error knowledge-editor-error">{error}</div>}

      <div className="knowledge-editor-body">
        {mode !== "view" && (
          <div className="knowledge-editor-column">
            <div className="knowledge-editor-title">
              <input
                placeholder={t("ai.knowledge_item_title_2")}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
              <span>{t("ai.agent_quotes_title_its_reply")}</span>
            </div>

            <div className="knowledge-md-toolbar">
              {KNOWLEDGE_MARKDOWN_TOOLS.map((tool) => (tool.divider
                ? <i className="knowledge-md-divider" key={tool.key} />
                : (
                  <button
                    className={tool.accent ? "is-accent" : ""}
                    key={tool.key}
                    title={tool.title}
                    type="button"
                    onClick={() => {
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
              <span className="knowledge-editor-gap" />
              <span className="knowledge-md-format">GFM</span>
            </div>

            <div
              className="knowledge-editor-text"
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
                <div className="knowledge-editor-drop">
                  <Icon name="upload" size={30} strokeWidth={1.8} />
                  <strong>{t("ai.drop_attach_item")}</strong>
                  <span>{t("ai.file_becomes_attachment_link_text")}</span>
                </div>
              )}
            </div>

            <div className="knowledge-editor-status">
              <span>{knowledgeEditorStats(content)}</span>
              <span>{cursorPosition(content, caret)}</span>
              <span className="knowledge-editor-gap" />
              <span>
                {dirty
                  ? t("ai.edits_not_saved_chunks_rebuilt")
                  : autoSavedAt
                    ? t("time.autosaved_at", { time: fmt.time(autoSavedAt) })
                    : t("ai.everything_saved")}
              </span>
            </div>
          </div>
        )}

        {mode !== "edit" && (
          <div className="knowledge-preview-column">
            <div className="knowledge-preview-head">
              <span>{t("ai.preview_of", { what: asAgent ? t("ai.how_agent_will_answer") : t("ai.internal_material") })}</span>
              <span className="knowledge-editor-gap" />
              <button
                className={asAgent ? "is-active" : ""}
                title={t("ai.how_agent_quotes")}
                type="button"
                onClick={() => setAsAgent((current) => !current)}
              >
                <Icon name="message" size={13} strokeWidth={1.9} />{t("ai.how_agent_will_answer_2")}</button>
            </div>
            <div className="knowledge-preview-body">
              {asAgent ? (
                <div className="knowledge-fragments">
                  <p className="knowledge-fragments-note">
                    {t("ai.fragments_note", { chunks: tn("plural.chunks", chunks.length) })}
                  </p>
                  {chunks.map((chunk, index) => (
                    <article className="knowledge-fragment" key={index}>
                      <header><b>{t("ai.fragment_number", { number: index + 1 })}</b><small>{t("ai.characters_count", { count: fmt.number(chunk.length) })}</small></header>
                      <p>{chunk}</p>
                    </article>
                  ))}
                  {chunks.length === 0 && <p className="knowledge-rail-empty">{t("ai.empty_item_never_reaches_replies")}</p>}
                </div>
              ) : (
                <article className="knowledge-preview-article">
                  <h1>{title || t("ai.untitled")}</h1>
                  {description && <p className="knowledge-preview-lead">{description}</p>}
                  <MarkdownContent content={content} />
                  {attachments.map((attachment) => (
                    <div className="knowledge-preview-file" key={attachment.id}>
                      <i><Icon name={isImageAttachment(attachment) ? "image" : "file"} size={15} strokeWidth={1.8} /></i>
                      <span>
                        <strong>{attachment.name}</strong>
                        <small>{t("ai.attachment_agent_hands_link_customer")}</small>
                      </span>
                    </div>
                  ))}
                </article>
              )}
            </div>
          </div>
        )}

        <aside className="knowledge-editor-rail">
          <div className="knowledge-rail-fields">
            <label>
              <span>{t("ai.category")}</span>
              <span className="knowledge-select">
                <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                  {catalog.categories.map((item) => (
                    <option key={item.id} value={item.id}>
                      {knowledgeCategoryPath(catalog.categories, item.id) || item.name}
                    </option>
                  ))}
                </select>
                <Icon name="chevron" size={13} strokeWidth={2} />
              </span>
            </label>
            <label>
              <span>{t("ai.short_description")}<small>{t("ai.helps_search_agent")}</small></span>
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
            <div className="knowledge-rail-toggle">
              <span>
                <strong>{t("ai.used_replies")}</strong>
                <small>{t("ai.can_switched_off_without_deleting")}</small>
              </span>
              <button
                aria-label={t("ai.used_replies")}
                aria-pressed={isEnabled}
                className={`knowledge-switch${isEnabled ? " is-on" : ""}`}
                disabled={!canManage}
                type="button"
                onClick={() => setIsEnabled((current) => !current)}
              >
                <i />
              </button>
            </div>
          </div>

          <div className="knowledge-rail-block">
            <div className="knowledge-rail-head">
              <span>{t("ai.attachments")}</span>
              <button type="button" onClick={() => fileInputRef.current?.click()}>{t("common.upload")}</button>
            </div>
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
            <div
              className={`knowledge-rail-drop${railDropping ? " is-hot" : ""}`}
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

            <div className="knowledge-rail-files">
              {uploading && (
                <div className="knowledge-rail-file is-fresh">
                  <i><Icon name="file" size={14} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{uploading.name}</strong>
                    <small className="is-progress">{t("common.uploading_percent", { percent: uploading.percent })}</small>
                    <span className="knowledge-rail-progress"><i style={{ width: `${uploading.percent}%` }} /></span>
                  </span>
                </div>
              )}
              {queued.map((file) => (
                <div className="knowledge-rail-file is-fresh" key={`${file.name}-${file.lastModified}`}>
                  <i><Icon name="file" size={14} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{file.name}</strong>
                    <small className="is-progress">{t("ai.will_attached_after_saving")}</small>
                  </span>
                  <button
                    className="knowledge-rail-file-remove"
                    title={t("common.remove_file")}
                    type="button"
                    onClick={() => setQueued((current) => current.filter((item) => item !== file))}
                  >
                    <Icon name="trash" size={13} strokeWidth={1.9} />
                  </button>
                </div>
              ))}
              {attachments.map((attachment) => {
                const inserted = content.includes(attachment.url);
                return (
                  <div className="knowledge-rail-file" key={attachment.id}>
                    <i><Icon name={isImageAttachment(attachment) ? "image" : "file"} size={14} strokeWidth={1.8} /></i>
                    <span>
                      <strong>{attachment.name}</strong>
                      <small>{attachmentMeta(attachment, content)}</small>
                    </span>
                    {!inserted && (
                      <button
                        className="knowledge-rail-file-insert"
                        title={t("ai.insert_link_into_text")}
                        type="button"
                        onClick={() => insertText(`\n${attachmentMarkdown(attachment)}\n`)}
                      >
                        <Icon name="plus" size={14} strokeWidth={2} />
                      </button>
                    )}
                    <button
                      title={t("ai.copy_as_markdown")}
                      type="button"
                      onClick={() => void navigator.clipboard?.writeText(attachmentMarkdown(attachment))}
                    >
                      <Icon name="copy" size={13} strokeWidth={1.9} />
                    </button>
                    {canManage && (
                      <button className="knowledge-rail-file-remove" title={t("ai.delete_attachment")} type="button" onClick={() => void removeAttachment(attachment)}>
                        <Icon name="trash" size={13} strokeWidth={1.9} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="knowledge-rail-block">
            <div className="knowledge-rail-head">
              <span>{t("common.agents_2")}</span>
              <small>{t("ai.changed_by_bulk_action")}</small>
            </div>
            <div className="knowledge-rail-agents is-compact">
              {attached.map(({ agent, meta }) => (
                <div className="knowledge-rail-agent" key={agent.id}>
                  <i><Icon name="robot" size={12} strokeWidth={1.8} /></i>
                  <span>
                    <strong>{agent.name}</strong>
                    <small>{meta}</small>
                  </span>
                </div>
              ))}
              {attached.length === 0 && <p className="knowledge-rail-empty">{t("ai.no_agents_yet")}</p>}
            </div>
            <p className="knowledge-rail-note">
              {t("ai.attach_detach_note")}
            </p>
            {loaded && canManage && (
              <button
                className="knowledge-reindex-button"
                disabled={busy}
                type="button"
                onClick={() => void reindexKnowledge(loaded.id).then(load).catch(() => setError(t("ai.could_not_reindex_knowledge_item")))}
              >
                <Icon name="undo" size={13} strokeWidth={1.9} />{t("ai.reindex")}</button>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
