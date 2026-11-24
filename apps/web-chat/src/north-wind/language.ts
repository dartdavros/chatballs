import { createI18n, normalizeLanguage, resolveLanguage } from "@chatballs/shared";

import { en } from "./messages.en";
import { ru, type ShopMessageKey } from "./messages.ru";
import { exchangeEn } from "./exchange/messages.en";
import { exchangeRu } from "./exchange/messages.ru";

const i18n = createI18n<ShopMessageKey | keyof typeof exchangeRu>({
  catalogs: {ru: {...ru, ...exchangeRu}, en: {...en, ...exchangeEn}}, source: "ru",
});
export const {t, tn, fmt} = i18n;

export function applyShopLanguage(language: string) {
  const code = normalizeLanguage(language);
  if (!code) return;
  i18n.setLanguage(code);
  document.documentElement.lang = code;
  document.title = t("shop_title");
}

export function initializeShopLanguage(linkLanguage: string | null) {
  applyShopLanguage(resolveLanguage({organization: linkLanguage}));
}
