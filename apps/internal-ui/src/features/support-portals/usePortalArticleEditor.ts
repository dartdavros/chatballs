import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
  fileMarkdown,
  fileMeta,
  isImageFile,
} from "../../shared/markdown/markdownTools";
import { t } from "../../i18n";

type Mode = "edit" | "split" | "view";

type UploadingFile = { name: string; percent: number };

function draftKey(portalId: number, articleId: number | null): string {
  return `chatballs:portal-article-draft:${portalId}:${articleId ?? "new"}`;
}

export function usePortalArticleEditor({
  article,
  categories,
  portal,
  onPublish,
  onSaved,
}: {
  article: PortalArticle | null;
  categories: PortalCategory[];
  portal: SupportPortal;
  onPublish: (article: PortalArticle, revisionId: number) => void;
  onSaved: () => Promise<void>;
}) {
  const portalId = portal.id;
  const [loaded, setLoaded] = useState<PortalArticle | null>(article);
  const [mode, setMode] = useState<Mode>("split");
  const [categoryId, setCategoryId] = useState(String(article?.category.id ?? categories.find(item => item.isSystem)?.id ?? ""));
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
  const category = categories.find((item) => item.id === Number(categoryId))
    ?? (loaded?.category.id === Number(categoryId) ? loaded.category : undefined);

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
          categoryId: categoryId ? Number(categoryId) : null,
          locale,
          slug,
        });
        const payload = await addArticleRevision(portalId, loaded.id, { title, summary, content });
        const detail = await loadPortalArticle(portalId, loaded.id);
        setLoaded(detail.article);
        setCategoryId(String(detail.article.category.id));
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
          categoryId: categoryId ? Number(categoryId) : null,
          slug,
          locale,
          title,
          summary,
          content,
        });
        window.localStorage.removeItem(draftKey(portalId, null));
        setLoaded(created.article);
        setCategoryId(String(created.article.category.id));
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
    if (latest && category?.id === loaded.category.id && locale === loaded.locale && slug === loaded.slug
      && latest.title === title && latest.summary === summary && latest.content === content) {
      onPublish(loaded, latest.id);
      return;
    }
    const saved = await save();
    if (saved) onPublish(saved.article, saved.revisionId);
  }

  const ready = Boolean(title.trim() && content.trim() && slug.trim());
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
  return { mode, setMode, category, categories, categoryId, setCategoryId, locale, setLocale, summary, setSummary,
    fileInputRef, imageInputRef, upload, railDropping, setRailDropping, uploading, files, content, insertText,
    removeFile, loaded, revisions, publishedRevisionId, selectedRevisionId, selectRevision, title, setTitle,
    editingSlug, setEditingSlug, slug, setSlug, textRef, applyEdit, setContent, setDropping, setCaret, dropping,
    caret, autoSavedAt, portal, busy, ready, save, publish, badge, error };
}

export type PortalArticleEditorState = ReturnType<typeof usePortalArticleEditor>;
