// Применение персональной темы и акцента (SPEC-HUB-0031 §7, дизайн-базлайн v2).
// Тема ставится атрибутом data-theme на <html>; акцент — переменной --primary,
// производные оттенки считаются в CSS через color-mix и работают в обеих темах.

export type UiTheme = "LIGHT" | "DARK" | "SYSTEM";

export const DEFAULT_ACCENT = "#1677ff";

// Пресеты акцента из дизайн-базлайна v2 (Tweaks макета).
export const ACCENT_PRESETS: Array<[string, string]> = [
  ["#1677ff", "Синий"],
  ["#6d5dfc", "Индиго"],
  ["#0f9b8e", "Бирюзовый"],
  ["#e8590c", "Оранжевый"],
];

const media = typeof window !== "undefined" && window.matchMedia
  ? window.matchMedia("(prefers-color-scheme: dark)")
  : null;

let currentTheme: UiTheme = "SYSTEM";
let listenerBound = false;

export function resolvedDark(theme: UiTheme): boolean {
  if (theme === "DARK") return true;
  if (theme === "LIGHT") return false;
  return Boolean(media?.matches);
}

export function applyAppearance(theme: UiTheme, accent: string): void {
  currentTheme = theme;
  const root = document.documentElement;
  root.dataset.theme = resolvedDark(theme) ? "dark" : "light";
  root.style.setProperty("--primary", accent || DEFAULT_ACCENT);
  if (media && !listenerBound) {
    listenerBound = true;
    media.addEventListener("change", () => {
      if (currentTheme === "SYSTEM") {
        document.documentElement.dataset.theme = media.matches ? "dark" : "light";
      }
    });
  }
}
