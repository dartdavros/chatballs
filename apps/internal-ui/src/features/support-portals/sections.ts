import type { Icon } from "../../shared/icons";

type IconName = Parameters<typeof Icon>[0]["name"];

export type PortalSettingsSectionKey =
  | "basics"
  | "domain"
  | "theme"
  | "widget"
  | "danger";

export type PortalSettingsSection = {
  key: PortalSettingsSectionKey;
  label: string;
  icon: IconName;
  heading: string;
  lead: string;
  // Разделитель под пунктом — как в макете, перед сноской субменю.
  divider?: boolean;
};

// Субменю настроек портала (дизайн-базлайн v2, кадры PT4–PT6). Модалки нет:
// настройки — страница /portals/{id}/settings/{раздел}.
export const PORTAL_SETTINGS_SECTIONS: PortalSettingsSection[] = [
  {
    key: "basics",
    label: "Основные",
    icon: "settings",
    heading: "Основные",
    lead: "Название, публичный адрес и язык материалов портала.",
  },
  {
    key: "domain",
    label: "Адрес и домен",
    icon: "globe",
    heading: "Свой домен",
    lead: "Портал будет открываться по адресу вашей компании. Адрес установки продолжит работать.",
  },
  {
    key: "theme",
    label: "Оформление",
    icon: "paint",
    heading: "Оформление",
    lead: "Тема публичных страниц и цветовая схема. Применяется до первого кадра — посетитель не видит смены оформления. Список тем — из сборки установки.",
  },
  {
    key: "widget",
    label: "Веб-виджет",
    icon: "widget",
    heading: "Веб-виджет",
    lead: "Публичный чат отображается на всех страницах портала.",
  },
  {
    key: "danger",
    label: "Публикация и архив",
    icon: "danger",
    heading: "Публикация и архив",
    lead: "Публикация открывает материалы посетителям, архив прячет портал целиком.",
    divider: true,
  },
];

export const DEFAULT_PORTAL_SETTINGS_SECTION: PortalSettingsSectionKey = "basics";

export function portalSettingsSectionKey(value: string): PortalSettingsSectionKey | null {
  const found = PORTAL_SETTINGS_SECTIONS.find((section) => section.key === value);
  return found ? found.key : null;
}
