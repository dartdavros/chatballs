import { t } from "../../i18n";
import type { SessionUser } from "../../types";
import { visibleSettingsSections, type SettingsSection, type SettingsSectionKey } from "./sections";

// Настройки организации и обслуживания. Подключения и сценарии доступны
// напрямую из главного меню; настройки установки — её администратору.
const GROUPS: { key: string; label: string; sections: SettingsSectionKey[] }[] = [
  { key: "organization", label: t("settings.navigation.organization"), sections: ["organization", "groups"] },
  { key: "service", label: t("settings.navigation.service"), sections: ["queue", "rules", "transfer", "templates", "communication"] },
  { key: "quality", label: t("settings.navigation.quality"), sections: ["ratings", "quality"] },
  { key: "other", label: t("settings.navigation.other"), sections: ["storage", "platform", "demo"] },
];

export function visibleSettingsGroups(user: SessionUser) {
  const sections = new Map(visibleSettingsSections(user).map(section => [section.key, section]));
  return GROUPS.map(group => ({
    ...group,
    sections: group.sections.map(key => sections.get(key)).filter((section): section is SettingsSection => !!section),
  })).filter(group => group.sections.length > 0);
}
