import { useEffect, useMemo, useState } from "react";

import { fetchHelpArticles } from "./api";
import { HelpArrowIcon, HelpFolderIcon } from "./HelpIcons";
import { HelpLayout } from "./HelpLayout";
import { HelpSearch } from "./HelpSearch";
import type { HelpArticle, HelpManifest } from "./types";

function articleHref(articleSlug: string): string {
  return `/articles/${encodeURIComponent(articleSlug)}/`;
}

function articleCount(value: number): string {
  const mod100 = value % 100;
  const mod10 = value % 10;
  const word = mod100 >= 11 && mod100 <= 14
    ? "статей"
    : mod10 === 1 ? "статья" : mod10 >= 2 && mod10 <= 4 ? "статьи" : "статей";
  return `${value} ${word}`;
}

export function HelpHome({ manifest }: { manifest: HelpManifest }) {
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [category, setCategory] = useState(params.get("category") ?? "");
  const [articles, setArticles] = useState<HelpArticle[] | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!search.trim() && !category) {
      setArticles([]);
      setFailed(false);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setFailed(false);
      setArticles(null);
      fetchHelpArticles({
        locale: manifest.portal.defaultLocale,
        category,
        query: search.trim(),
      })
        .then((payload) => {
          if (cancelled) return;
          setArticles(payload.items);
          setHasMore(payload.pagination.hasMore);
        })
        .catch(() => {
          if (cancelled) return;
          setFailed(true);
          setArticles([]);
        });
    }, search ? 180 : 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [category, manifest.portal.defaultLocale, search]);

  const filtering = Boolean(search.trim() || category);
  const selectedCategory = manifest.categories.find((item) => item.slug === category);

  function chooseCategory(slug: string) {
    setCategory(slug);
    const next = new URL(window.location.href);
    if (slug) next.searchParams.set("category", slug);
    else next.searchParams.delete("category");
    window.history.replaceState({}, "", next);
  }

  async function loadMore() {
    if (!articles) return;
    try {
      const payload = await fetchHelpArticles({
        locale: manifest.portal.defaultLocale,
        category,
        query: search.trim(),
        offset: articles.length,
      });
      setArticles((current) => [...(current ?? []), ...payload.items]);
      setHasMore(payload.pagination.hasMore);
    } catch {
      setFailed(true);
    }
  }

  return (
    <HelpLayout
      portal={manifest.portal}
      search={search}
      onSearchChange={setSearch}
    >
      <section className="help-hero">
        <HelpSearch value={search} onChange={setSearch} />
      </section>

      <section className="help-home-content">
        {filtering ? (
          <div className="help-results">
            <div className="help-results-heading">
              <div>
                <span>{selectedCategory ? selectedCategory.name : "Результаты поиска"}</span>
                <h1>{search.trim() ? `Поиск: «${search.trim()}»` : selectedCategory?.name}</h1>
              </div>
              <button type="button" onClick={() => { setSearch(""); chooseCategory(""); }}>
                Все разделы
              </button>
            </div>
            {failed ? (
              <div className="help-empty"><strong>Не удалось загрузить статьи</strong><span>Попробуйте обновить страницу.</span></div>
            ) : articles === null ? (
              <div className="help-loading-lines"><i /><i /><i /></div>
            ) : articles.length ? (
              <div className="help-article-results">
                {articles.map((article) => (
                  <a href={articleHref(article.slug)} key={`${article.locale}-${article.slug}`}>
                    <span>{article.category.name}</span>
                    <strong>{article.revision.title}</strong>
                    {article.revision.summary && <p>{article.revision.summary}</p>}
                    <HelpArrowIcon />
                  </a>
                ))}
                {hasMore && <button className="help-load-more" type="button" onClick={() => void loadMore()}>Показать ещё</button>}
              </div>
            ) : (
              <div className="help-empty"><strong>Ничего не найдено</strong><span>Попробуйте изменить запрос или открыть другой раздел.</span></div>
            )}
          </div>
        ) : (
          <div className="help-category-grid">
            {manifest.categories.filter((item) => item.parentId === null).map((item) => (
              <button type="button" key={item.id} onClick={() => chooseCategory(item.slug)}>
                <span className="help-category-icon"><HelpFolderIcon /></span>
                <span className="help-category-copy">
                  <strong>{item.name}</strong>
                  {item.description && <p>{item.description}</p>}
                  <small>{articleCount(item.articleCount)}</small>
                </span>
              </button>
            ))}
          </div>
        )}
      </section>
    </HelpLayout>
  );
}
