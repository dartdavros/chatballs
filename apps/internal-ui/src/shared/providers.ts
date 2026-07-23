/* Провайдеры подключений: MAX / Telegram / Web Chat.

   Общий словарь для всего приложения — раньше он лежал в демо-данных диалогов,
   и продуктовые экраны каналов зависели от файла с примерами.
   Провайдеры различаются точкой и коротким лейблом на своих токенах
   (ADR-HUB-0013), а не бренд-логотипами. */

export type ProviderKey = "MAX" | "TG" | "WEB";

export const providerMeta: Record<ProviderKey, { label: string; short: string; color: string; bg: string }> = {
  MAX: { label: "MAX", short: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
  TG: { label: "Telegram", short: "TG", color: "#2f8fd0", bg: "#eaf6fd" },
  WEB: { label: "Web Chat", short: "Web", color: "#0f9b8e", bg: "#e8f7f4" },
};

/** Код провайдера из API → ключ словаря. */
const BY_CODE: Record<string, ProviderKey> = {
  MAX: "MAX",
  TELEGRAM: "TG",
  TG: "TG",
  WEB: "WEB",
  WEBCHAT: "WEB",
};

export function providerKey(code: string): ProviderKey | null {
  return BY_CODE[code] ?? null;
}

export function providerLabel(code: string): string {
  const key = providerKey(code);
  return key ? providerMeta[key].label : code;
}
