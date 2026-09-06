// Контракт визуальной темы портала (SPEC-HUB-0028 §6, ADR-HUB-0044).
// Как сделать свою тему — themes/README.md.

export type PortalThemeScheme = "light" | "dark";

// Настройка схемы в карточке портала. Значения совпадают с UiTheme хаба
// (shared/appearance.ts): один стандарт на выбор светлой/тёмной темы.
export type PortalThemeSchemeSetting = "LIGHT" | "DARK" | "SYSTEM";

export type PortalThemeManifest = {
  // Совпадает с именем папки темы, проверяется тестом реестра.
  id: string;
  name: string;
  description: string;
  // Схемы, которые тема реально поддерживает. Первая — основная: на неё
  // деградирует портал, если сохранённая схема темой не поддержана.
  schemes: PortalThemeScheme[];
  // Три цвета для превью в настройках портала: подложка, текст, акцент.
  preview: { bg: string; ink: string; accent: string };
  author?: string;
};
