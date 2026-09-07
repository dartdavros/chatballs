import type { Icon } from "../../shared/icons";

// Разделы «Настроек» (дизайн-базлайн v2, кадры N1–N7): субменю 240px и один
// раздел на экране вместо сплошной ленты секций. Профиль пользователя сюда не
// входит — это отдельная страница из меню пользователя.

export type SettingsSectionKey =
  | "organization"
  | "groups"
  | "ai"
  | "integrations"
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
  // Табличные разделы шире: 1000px против 820px у остальных (кадры N3–N5).
  wide?: boolean;
};

export const SETTINGS_SECTIONS: SettingsSection[] = [
  {
    key: "organization",
    label: "Организация",
    icon: "building",
    heading: "Организация",
    lead: "Название, логотип и региональные параметры. Видны сотрудникам, в виджете и письмах.",
    // Адрес установки и почта сюда не входят — это свойства инсталляции, а не
    // организации, и живут в разделе «Платформа». Раздел равен кадру N1.
  },
  {
    key: "groups",
    label: "Группы",
    icon: "team",
    heading: "Группы",
    lead: "Делят диалоги между сотрудниками: сотрудник видит диалоги своих групп, без группы и те, где он ответственный.",
  },
  {
    key: "ai",
    label: "AI-провайдер",
    icon: "sparkles",
    heading: "AI-провайдер",
    lead: "Ключи вашей организации для ответов агентов и расшифровки голосовых. Модель выбирается на карточке агента.",
    wide: true,
  },
  {
    key: "integrations",
    label: "Интеграции",
    icon: "plug",
    heading: "Интеграции",
    lead: "Боты, почта и Web-виджет — точки входа диалогов. Каждая привязана к агенту, который отвечает первым.",
    wide: true,
  },
  {
    key: "communication",
    label: "Голосовые и звонки",
    icon: "mic",
    heading: "Голосовые и звонки",
    lead: "Где клиент и сотрудник могут записывать голосовые и начинать аудио- и видеозвонки.",
    wide: true,
  },
  {
    key: "storage",
    label: "Хранилище файлов",
    icon: "database",
    heading: "Хранилище файлов",
    lead: "Вложения, голосовые, фото и логотипы — на диске установки или во внешнем S3-совместимом хранилище.",
  },
  {
    key: "platform",
    label: "Платформа",
    icon: "globe",
    heading: "Платформа",
    lead: "Свойства самой установки: адрес, по которому её открывают и по которому строятся ссылки на файлы, и почтовый сервер для приглашений и сброса пароля.",
  },
  {
    key: "demo",
    label: "Демо-данные",
    icon: "sun",
    heading: "Демо-данные",
    lead: "Посмотреть систему в работе на вымышленной организации.",
  },
];

export const DEFAULT_SETTINGS_SECTION: SettingsSectionKey = "organization";

export function settingsSectionKey(value: string | null | undefined): SettingsSectionKey | null {
  const found = SETTINGS_SECTIONS.find((section) => section.key === value);
  return found ? found.key : null;
}
