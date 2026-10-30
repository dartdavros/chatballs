import type { Icon } from "../../shared/icons";
import type { SessionUser } from "../../types";
import { t } from "../../i18n";

// Разделы «Настроек» (дизайн-базлайн v2, кадры N1–N7): субменю 240px и один
// раздел на экране вместо сплошной ленты секций. Профиль пользователя сюда не
// входит — это отдельная страница из меню пользователя.

export type SettingsSectionKey =
  | "organization"
  | "groups"
  | "queue"
  | "rules"
  | "transfer"
  | "templates"
  | "ratings"
  | "quality"
  | "ai"
  | "integrations"
  | "scenarios"
  | "communication"
  | "storage"
  | "platform"
  | "demo";

export type SettingsSection = {
  key: SettingsSectionKey;
  label: string;
  icon: Parameters<typeof Icon>[0]["name"];
  heading: string;
  lead: string;
  // Раздел про саму установку: виден только администратору установки.
  instanceOnly?: boolean;
};

export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    key: "organization",
    label: t("settings.organization"),
    icon: "building",
    heading: t("settings.organization"),
    lead: t("settings.name_logo_regional_settings_visible"),
    // Адрес установки и почта сюда не входят — это свойства инсталляции, а не
    // организации, и живут в разделе «Платформа». Раздел равен кадру N1.
  },
  {
    key: "groups",
    label: t("common.groups"),
    icon: "team",
    heading: t("common.groups"),
    lead: t("settings.they_split_conversations_between_operators"),
  },
  {
    key: "queue",
    label: t("settings.when_to_call_for_help"),
    icon: "clock",
    heading: t("settings.when_to_call_for_help"),
    lead: t("settings.queue_section_lead"),
  },
  {
    key: "rules",
    label: t("handling_rules.title"),
    icon: "clock",
    heading: t("handling_rules.title"),
    lead: t("handling_rules.lead"),
  },
  {
    key: "transfer",
    label: t("transfers.title"),
    icon: "transfer",
    heading: t("transfers.title"),
    lead: t("transfers.lead"),
  },
  {
    // Своего кадра в базлайне нет: раздел согласован по образцу «Групп» (N2).
    key: "templates",
    label: t("settings.reply_templates"),
    icon: "text",
    heading: t("settings.reply_templates"),
    lead: t("settings.reply_templates_lead"),
  },
  {
    key: "ratings",
    label: t("ratings.title"),
    icon: "thumbUp",
    heading: t("ratings.title"),
    lead: t("ratings.lead"),
  },
  {
    key: "quality",
    label: t("quality.title"),
    icon: "sparkles",
    heading: t("quality.title"),
    lead: t("quality.lead"),
  },
  {
    key: "ai",
    label: t("settings.ai_provider"),
    icon: "sparkles",
    heading: t("settings.ai_provider"),
    lead: t("settings.organization_s_keys_agent_replies"),
  },
  {
    key: "integrations",
    label: t("common.integrations"),
    icon: "plug",
    heading: t("common.integrations"),
    lead: t("services.section_lead"),
  },
  {
    key: "scenarios",
    label: t("scenarios.title"),
    icon: "refresh",
    heading: t("scenarios.title"),
    lead: t("scenarios.lead"),
  },
  {
    key: "communication",
    label: t("settings.voice_calls"),
    icon: "mic",
    heading: t("settings.voice_calls"),
    lead: t("settings.where_customer_operator_can_record"),
  },
  {
    key: "storage",
    label: t("settings.file_storage"),
    icon: "database",
    heading: t("settings.file_storage"),
    lead: t("settings.attachments_voice_messages_photos_logos"),
    instanceOnly: true,
  },
  {
    key: "platform",
    label: t("settings.platform"),
    icon: "globe",
    heading: t("settings.platform"),
    lead: t("settings.properties_installation_itself_address_opened"),
    instanceOnly: true,
  },
  {
    key: "demo",
    label: t("settings.demo_data"),
    icon: "sun",
    heading: t("settings.demo_data"),
    lead: t("settings.see_system_at_work_fictional"),
  },
];

export const DEFAULT_SETTINGS_SECTION: SettingsSectionKey = "organization";

export function visibleSettingsSections(user: SessionUser): SettingsSection[] {
  return SETTINGS_SECTIONS.filter((section) => !section.instanceOnly || user.isInstanceAdmin);
}

export function settingsSectionKey(value: string | null | undefined): SettingsSectionKey | null {
  const found = SETTINGS_SECTIONS.find((section) => section.key === value);
  return found ? found.key : null;
}
