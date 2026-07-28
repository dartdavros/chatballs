import { useEffect, useMemo, useState } from "react";

import { ContentEditorBreadcrumb } from "../../shared/content-library/ContentEditorBreadcrumb";
import { ContentEditorCard } from "../../shared/content-library/ContentEditorCard";
import { FormField, SelectField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { formatDate } from "../../shared/utils";
import {
  addArticleRevision,
  createPortalArticle,
  loadPortalArticle,
  portalErrorMessage,
  updatePortalArticle,
  type PortalArticle,
  type PortalCategory,
} from "./model";

export function PortalArticleEditor({
  article,
  categories,
  defaultLocale,
  onClose,
  onPublish,
  onSaved,
  portalId,
}: {
  article: PortalArticle | null;
  categories: PortalCategory[];
  defaultLocale: string;
  onClose: () => void;
  onPublish: (article: PortalArticle, revisionId: number) => void;
  onSaved: () => Promise<void>;
  portalId: number;
}) {
  const [loaded, setLoaded] = useState<PortalArticle | null>(article);
  const [categoryId, setCategoryId] = useState(String(article?.category.id ?? categories[0]?.id ?? ""));
  const [locale, setLocale] = useState(article?.locale ?? defaultLocale);
  const [slug, setSlug] = useState(article?.slug ?? "");
  const [selectedRevisionId, setSelectedRevisionId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(Boolean(article));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!article) return;
    setBusy(true);
    loadPortalArticle(portalId, article.id)
      .then(({ article: detail }) => {
        setLoaded(detail);
        const revision = detail.revisions?.[0] ?? detail.publishedRevision;
        setSelectedRevisionId(revision?.id ?? null);
        setTitle(revision?.title ?? "");
        setSummary(revision?.summary ?? "");
        setContent(revision?.content ?? "");
      })
      .catch((caught) => setError(portalErrorMessage(caught, "Не удалось загрузить статью")))
      .finally(() => setBusy(false));
  }, [article, portalId]);

  const revisions = useMemo(() => loaded?.revisions ?? [], [loaded]);

  function selectRevision(value: string) {
    const revision = revisions.find((item) => item.id === Number(value));
    if (!revision) return;
    setSelectedRevisionId(revision.id);
    setTitle(revision.title);
    setSummary(revision.summary);
    setContent(revision.content);
  }

  async function save() {
    setBusy(true);
    setError("");
    try {
      if (article) {
        await updatePortalArticle(portalId, article.id, {
          categoryId: Number(categoryId),
          locale,
          slug,
        });
        const payload = await addArticleRevision(portalId, article.id, { title, summary, content });
        const detail = await loadPortalArticle(portalId, article.id);
        setLoaded(detail.article);
        setSelectedRevisionId(payload.revision.id);
      } else {
        await createPortalArticle(portalId, {
          categoryId: Number(categoryId),
          slug,
          locale,
          title,
          summary,
          content,
        });
      }
      await onSaved();
      if (!article) onClose();
    } catch (caught) {
      setError(portalErrorMessage(caught, "Не удалось сохранить статью"));
    } finally {
      setBusy(false);
    }
  }

  const ready = Boolean(title.trim() && content.trim() && (article || (categoryId && slug.trim())));
  const categoryName = categories.find((item) => item.id === Number(categoryId))?.name;
  const active = loaded?.status === "PUBLISHED";

  return (
    <div className="knowledge-editor-page">
      <ContentEditorBreadcrumb
        backLabel="Материалы"
        category={categoryName}
        title={article?.latestRevision?.title ?? "Создание статьи"}
        onBack={onClose}
      />
      <div className="knowledge-editor-grid create">
        <div className="knowledge-editor-main">
          <ContentEditorCard
            heading={<h3>{article ? "Статья" : "Новая статья"}</h3>}
            meta={<><span className={`knowledge-card-status${active ? "" : " disabled"}`}><i />{active ? "Опубликована" : "Черновик"}</span>{loaded && <span className="knowledge-card-updated">обновлено {formatDate(loaded.updatedAt)}</span>}</>}
            error={error}
            actions={<>
              <Button variant="primary" icon={article ? "save" : "plus"} disabled={busy || !ready} onClick={() => void save()}>
                {article ? "Сохранить новую версию" : "Создать статью"}
              </Button>
              {article && selectedRevisionId && (
                <Button variant="secondary" disabled={busy} onClick={() => onPublish(article, selectedRevisionId)}>
                  Опубликовать версию
                </Button>
              )}
            </>}
          >
            <div className="knowledge-editor-fields">
              <div className="knowledge-editor-scope-row">
            <SelectField label="Раздел" value={categoryId} onChange={setCategoryId} options={categories.map((category) => [String(category.id), category.name])} />
            <SelectField label="Язык" value={locale} onChange={setLocale} options={[["ru", "Русский"], ["en", "English"]]} />
              </div>
              <div className="knowledge-editor-scope-row">
                <FormField label="Адрес статьи" value={slug} onChange={setSlug} mono wide />
                {article && revisions.length > 0 && (
                  <SelectField
                    label="Версия"
                    value={String(selectedRevisionId ?? "")}
                    onChange={selectRevision}
                    options={revisions.map((revision) => [
                      String(revision.id),
                      `Версия ${revision.revision}${revision.id === article.publishedRevision?.id ? " · опубликована" : ""}`,
                    ])}
                  />
                )}
              </div>
              <FormField label="Заголовок" value={title} onChange={setTitle} wide />
              <TextAreaField label="Краткое описание" value={summary} onChange={setSummary} />
              <label className="knowledge-content-field">
                <span>Содержимое (Markdown)</span>
                <textarea value={content} rows={10} onChange={(event) => setContent(event.target.value)} />
              </label>
            </div>
          </ContentEditorCard>
        </div>
      </div>
    </div>
  );
}
