// Язык интерфейса: словарь, форматы и список языков.
//
// Список языков и правило выбора продублированы с бэкендом
// (chatballs/i18n/languages.py) намеренно: виджет открывается у клиента до
// любого запроса к API и должен знать свой язык сразу, а рабочее место —
// показать логин на нужном языке ещё до того, как узнает, кто вошёл.
// Расхождение ловится тестом, который сверяет оба списка.

import { currentLanguage, onLanguageChange, setCurrentLanguage } from "./current";
import { createFormats, type ByteUnitKey, type Formats } from "./formats";
import { createTranslator, type Catalog, type Message, type Params, type PluralCategory } from "./engine";

export { createFormats, createTranslator, currentLanguage, onLanguageChange, setCurrentLanguage };
export type { ByteUnitKey, Catalog, Formats, Message, Params, PluralCategory };

export type LanguageCode = "ru" | "en";

/** Подпись — на самом языке: свой язык человек узнает в любом интерфейсе. */
export const LANGUAGES: ReadonlyArray<{ code: LanguageCode; label: string }> = [
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
];

export const LANGUAGE_CODES: readonly LanguageCode[] = LANGUAGES.map((item) => item.code);

export const DEFAULT_LANGUAGE: LanguageCode = "ru";

/**
 * Привести код к поддерживаемому языку. Пустая строка — «выбора нет»:
 * так пишется и «как в организации» в профиле, и «как в установке» в
 * организации, поэтому неизвестный язык сводится к ней, а не к ошибке.
 */
export function normalizeLanguage(value: string | null | undefined): LanguageCode | "" {
  if (!value) return "";
  const base = value.trim().replace("_", "-").toLowerCase().split("-")[0];
  return (LANGUAGE_CODES as readonly string[]).includes(base) ? (base as LanguageCode) : "";
}

/** Язык браузера — последний рубеж: работает до входа, когда выбора ещё нет. */
export function browserLanguage(): LanguageCode | "" {
  if (typeof navigator === "undefined") return "";
  for (const candidate of navigator.languages ?? [navigator.language]) {
    const code = normalizeLanguage(candidate);
    if (code) return code;
  }
  return "";
}

/** Тот же порядок, что и на бэкенде: профиль, организация, установка, браузер. */
export function resolveLanguage(sources: {
  user?: string | null;
  organization?: string | null;
  instance?: string | null;
}): LanguageCode {
  for (const value of [sources.user, sources.organization, sources.instance]) {
    const code = normalizeLanguage(value);
    if (code) return code;
  }
  return browserLanguage() || DEFAULT_LANGUAGE;
}

export type I18n<K extends string> = ReturnType<typeof createTranslator<K>> & { fmt: Formats };

/** Собрать переводчик и форматы, привязанные к одному текущему языку. */
export function createI18n<K extends string>(options: { catalogs: Record<string, Catalog<K>>; source: string }): I18n<K> {
  const translator = createTranslator(options);
  return Object.assign(translator, { fmt: createFormats(translator.language) });
}
