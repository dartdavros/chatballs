import { shortDateTime } from "../../shared/utils";
import type { PortalArticle, SupportPortal } from "./model";
import { fmt, t, tn } from "../../i18n";

const LOCALE_NAMES: Record<string, string> = {
  ru: t("portals.russian_2"),
  en: t("portals.english"),
};

export const LOCALE_OPTIONS: Array<[string, string]> = [
  ["ru", t("portals.russian")],
  ["en", "English"],
];

export function localeName(locale: string): string {
  return LOCALE_NAMES[locale] ?? locale;
}

/** «русский · создан 12 июля» — вторая строка названия портала (кадр PT1). */
export function portalSubtitle(portal: SupportPortal): string {
  const created = fmt.dayMonthLong(portal.createdAt);
  return t("portals.locale_created", { locale: localeName(portal.defaultLocale), date: created });
}

/** «6 разделов · 48 статей» — колонка «Материалы» и подзаголовок карточки. */
export function contentSummary(portal: SupportPortal): string {
  return [
    tn("plural.sections", portal.categoryCount),
    tn("plural.articles", portal.articleCount),
  ].join(" · ");
}

/** Публичный адрес без схемы: в макете колонка и шапка показывают только хост. */
export function publicHost(portal: SupportPortal): string {
  return portal.publicUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

export function hostedHost(portal: SupportPortal): string {
  return portal.hostedDomain.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

export function updatedAt(value: string): string {
  return shortDateTime(value);
}

/** «Редакция 7 · черновая 8» — колонка «Редакция» таблицы статей (кадр PT3). */
export function revisionSummary(article: PortalArticle): {
  revision: string;
  note: string;
} {
  const published = article.publishedRevision?.revision ?? null;
  const latest = article.latestRevision?.revision ?? null;
  if (published === null) {
    return { revision: latest === null ? "—" : String(latest), note: t("portals.not_published") };
  }
  return {
    revision: String(published),
    note: latest !== null && latest > published ? t("portals.draft_revision", { revision: latest }) : "",
  };
}
