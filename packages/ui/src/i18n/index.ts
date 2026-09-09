// Перевод общих компонентов. Язык не выбирается здесь: его ставит приложение,
// а пакет только читает общий текущий язык из @chatballs/shared.

import { createI18n } from "@chatballs/shared";

import { en } from "./en";
import { ru, type UiMessageKey } from "./ru";

const i18n = createI18n<UiMessageKey>({ catalogs: { ru, en }, source: "ru" });

export type { UiMessageKey };
export const t = i18n.t;
