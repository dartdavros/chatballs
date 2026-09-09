// Язык виджета.
//
// Виджет открывается у клиента на чужой странице, и профиля здесь нет. Язык
// приходит вместе с настройками виджета — это язык организации, на котором
// отвечают и агент, и оператор; английская обвязка вокруг русских ответов
// читалась бы как поломка. Пока настройки не загрузились (а это первый кадр),
// работает язык браузера посетителя.

import { createI18n, resolveLanguage, setCurrentLanguage } from "@chatballs/shared";

import { en } from "./en";
import { ru, type ChatMessageKey } from "./ru";

const i18n = createI18n<ChatMessageKey>({ catalogs: { ru, en }, source: "ru" });
i18n.setLanguage(resolveLanguage({}));

export type { ChatMessageKey };
export const t = i18n.t;
export const fmt = i18n.fmt;

/** Принять язык из настроек виджета. Пустое значение оставляет язык браузера. */
export function applyWidgetLanguage(language: string | undefined): void {
  if (language) setCurrentLanguage(language);
}
