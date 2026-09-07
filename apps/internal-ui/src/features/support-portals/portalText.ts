import { pluralRu, shortDateTime } from "../../shared/utils";
import type { PortalArticle, SupportPortal } from "./model";

const LOCALE_NAMES: Record<string, string> = {
  ru: "русский",
  en: "английский",
};

export const LOCALE_OPTIONS: Array<[string, string]> = [
  ["ru", "Русский"],
  ["en", "English"],
];

export function localeName(locale: string): string {
  return LOCALE_NAMES[locale] ?? locale;
}

/** «русский · создан 12 июля» — вторая строка названия портала (кадр PT1). */
export function portalSubtitle(portal: SupportPortal): string {
  const created = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" })
    .format(new Date(portal.createdAt));
  return `${localeName(portal.defaultLocale)} · создан ${created}`;
}

/** «6 разделов · 48 статей» — колонка «Материалы» и подзаголовок карточки. */
export function contentSummary(portal: SupportPortal): string {
  return [
    pluralRu(portal.categoryCount, ["раздел", "раздела", "разделов"]),
    pluralRu(portal.articleCount, ["статья", "статьи", "статей"]),
  ].join(" · ");
}

export function productsSummary(portal: SupportPortal): string {
  return portal.products.length
    ? pluralRu(portal.products.length, ["продукт", "продукта", "продуктов"])
    : "—";
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
    return { revision: latest === null ? "—" : String(latest), note: "не опубликована" };
  }
  return {
    revision: String(published),
    note: latest !== null && latest > published ? `черновая ${latest}` : "",
  };
}
