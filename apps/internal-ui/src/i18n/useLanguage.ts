import { useSyncExternalStore } from "react";

import { onLanguageChange } from "@chatballs/shared";

import { language } from "./index";

/**
 * Перерисовать компонент при смене языка.
 *
 * Нужен ровно там, где язык меняют на живом экране, — в мастере первого
 * запуска. В остальном интерфейсе смена языка перезагружает страницу, и
 * подписываться не на что.
 */
export function useLanguage(): string {
  return useSyncExternalStore(onLanguageChange, language, language);
}
