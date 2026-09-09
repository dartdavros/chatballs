import type { Icon } from "../../shared/icons";
import { t } from "../../i18n";

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
    label: t("portals.basics"),
    icon: "settings",
    heading: t("portals.basics"),
    lead: t("portals.portal_s_name_public_address"),
  },
  {
    key: "domain",
    label: t("portals.address_domain"),
    icon: "globe",
    heading: t("portals.custom_domain"),
    lead: t("portals.portal_will_open_at_company"),
  },
  {
    key: "theme",
    label: t("common.appearance"),
    icon: "paint",
    heading: t("common.appearance"),
    lead: t("portals.theme_colour_scheme_public_pages"),
  },
  {
    key: "widget",
    label: t("common.web_widget_2"),
    icon: "widget",
    heading: t("common.web_widget_2"),
    lead: t("portals.public_chat_appears_every_portal"),
  },
  {
    key: "danger",
    label: t("portals.publishing_archive"),
    icon: "danger",
    heading: t("portals.publishing_archive"),
    lead: t("portals.publishing_opens_material_visitors_archive"),
    divider: true,
  },
];

export const DEFAULT_PORTAL_SETTINGS_SECTION: PortalSettingsSectionKey = "basics";

export function portalSettingsSectionKey(value: string): PortalSettingsSectionKey | null {
  const found = PORTAL_SETTINGS_SECTIONS.find((section) => section.key === value);
  return found ? found.key : null;
}
