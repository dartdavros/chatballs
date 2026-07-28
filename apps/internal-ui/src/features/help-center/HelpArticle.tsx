import { useEffect, useMemo, useState } from "react";

import { fetchHelpArticle, sendArticleFeedback } from "./api";
import { HelpChevronIcon, HelpThumbIcon } from "./HelpIcons";
import { HelpLayout } from "./HelpLayout";
import { MarkdownContent, parseMarkdown } from "./MarkdownContent";
import type { HelpArticle as HelpArticleType, HelpManifest } from "./types";

function formattedDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

export function HelpArticle({
  manifest,
  articleSlug,
}: {
  manifest: HelpManifest;
  articleSlug: string;
}) {
  const [article, setArticle] = useState<HelpArticleType | null>(null);
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState<"idle" | "sending" | "sent" | "error">("idle");

  useEffect(() => {
    fetchHelpArticle(articleSlug, manifest.portal.defaultLocale)
      .then((payload) => setArticle(payload.article))
      .catch(() => setFailed(true));
  }, [articleSlug, manifest.portal.defaultLocale]);

  const headings = useMemo(
    () => article ? parseMarkdown(article.revision.content ?? "").headings.filter((item) => item.level <= 3) : [],
    [article],
  );
  const homeHref = "/";

  function searchSubmit(value: string) {
    const suffix = value ? `?q=${encodeURIComponent(value)}` : "";
    window.location.href = `${homeHref}${suffix}`;
  }

  async function vote(helpful: boolean) {
    if (!article || feedback === "sending" || feedback === "sent") return;
    setFeedback("sending");
    try {
      await sendArticleFeedback(
        article.slug,
        helpful,
        article.locale,
      );
      setFeedback("sent");
    } catch {
      setFeedback("error");
    }
  }

  return (
    <HelpLayout
      compactHeader
      portal={manifest.portal}
      search={search}
      onSearchChange={setSearch}
      onSearchSubmit={searchSubmit}
    >
      {failed ? (
        <section className="help-article-error">
          <strong>Статья не найдена</strong>
          <a href={homeHref}>Вернуться в базу знаний</a>
        </section>
      ) : !article ? (
        <section className="help-article-loading"><i /><i /><i /><i /></section>
      ) : (
        <div className="help-article-shell">
          <nav className="help-breadcrumbs" aria-label="Навигация">
            <a href={homeHref}>Все разделы</a>
            <HelpChevronIcon />
            <a href={`${homeHref}?category=${encodeURIComponent(article.category.slug)}`}>
              {article.category.name}
            </a>
            <HelpChevronIcon />
            <span>{article.revision.title}</span>
          </nav>
          <div className="help-article-grid">
            <article className="help-article">
              <header>
                <h1>{article.revision.title}</h1>
                {article.revision.summary && <p>{article.revision.summary}</p>}
                <time dateTime={article.updatedAt}>
                  Обновлено {formattedDate(article.updatedAt, article.locale)}
                </time>
              </header>
              <MarkdownContent content={article.revision.content ?? ""} />
              <section className="help-feedback">
                {feedback === "sent" ? (
                  <div className="help-feedback-thanks">
                    <strong>Спасибо за отзыв</strong>
                    <span>Он поможет сделать базу знаний полезнее.</span>
                  </div>
                ) : (
                  <>
                    <h2>Эта статья была полезна?</h2>
                    {feedback === "error" && <p role="alert">Не удалось отправить отзыв. Попробуйте ещё раз.</p>}
                    <div>
                      <button
                        aria-label="Да, статья полезна"
                        disabled={feedback === "sending"}
                        type="button"
                        onClick={() => void vote(true)}
                      >
                        <HelpThumbIcon direction="up" />
                      </button>
                      <button
                        aria-label="Нет, статья не помогла"
                        disabled={feedback === "sending"}
                        type="button"
                        onClick={() => void vote(false)}
                      >
                        <HelpThumbIcon direction="down" />
                      </button>
                    </div>
                  </>
                )}
              </section>
            </article>
            {headings.length > 0 && (
              <aside className="help-toc" aria-label="Содержание статьи">
                <strong>В этой статье</strong>
                <nav>
                  {headings.map((heading) => (
                    <a className={heading.level === 3 ? "is-nested" : ""} href={`#${heading.id}`} key={heading.id}>
                      {heading.title}
                    </a>
                  ))}
                </nav>
              </aside>
            )}
          </div>
        </div>
      )}
    </HelpLayout>
  );
}
