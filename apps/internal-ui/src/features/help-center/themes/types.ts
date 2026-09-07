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
  // Превью в настройках портала (кадр PT6): подложка, текст, акцент и
  // скругление плиток — тем же радиусом, каким тема скругляет карточки.
  preview: { bg: string; ink: string; accent: string; radius?: string };
  author?: string;
};
