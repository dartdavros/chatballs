// Proposed strings for the single S01 design; application catalogs are untouched.
export const copy = {
  ru: {
    title: 'Настройки внешнего исполнения · на утверждение',
    frame: 'S01 · Настройки → Обслуживание → Внешнее исполнение',
    reviewNote: 'Статический дизайн, S01-r2. Источник — текущий код приложения. Примерные данные; сохранение и переходы не выполняются.',
    proposal: 'По вашему указанию: «Внешнее исполнение» — последний пункт группы «Обслуживание», с существующей иконкой сервера. Открыт отдельный раздел настроек. Опция выключена, форма подключения скрыта; следующий кадр — после вашего решения.',
    width: 'Ширина', theme: 'Тема', language: 'Язык', accent: 'Акцент', light: 'Светлая', dark: 'Тёмная',
    organizationName: 'Обед.ру', ownerName: 'Александр Ермолаев',
    sectionTitle: 'Внешнее исполнение',
    externalTitle: 'Внешнее исполнение агентов',
    externalDescription: 'Внешний сервис использует свою модель, знания и инструменты. Chatballs хранит переписку и доставляет ответы.',
    externalHelp: 'После включения здесь можно настроить внешний сервис, а в карточках агентов — выбрать способ исполнения.',
    externalPreserved: 'Включение не меняет способ исполнения существующих агентов.',
  },
  en: {
    title: 'External execution settings · for approval',
    frame: 'S01 · Settings → Service → External execution',
    reviewNote: 'Static design, S01-r2. Based on current application code. Illustrative data; saving and navigation are inactive.',
    proposal: 'As requested: External execution is the last item in the Service group, with the existing server icon. A dedicated settings section is open. The option is disabled and connection fields are hidden; the next frame follows your decision.',
    width: 'Width', theme: 'Theme', language: 'Language', accent: 'Accent', light: 'Light', dark: 'Dark',
    organizationName: 'Obed.ru', ownerName: 'Alexander Ermolaev',
    sectionTitle: 'External execution',
    externalTitle: 'External agent execution',
    externalDescription: 'The external service uses its own model, knowledge and tools. Chatballs stores conversations and delivers replies.',
    externalHelp: 'Once enabled, configure the external service here and choose the execution method in agent cards.',
    externalPreserved: 'Enabling this option does not change existing agents’ execution methods.',
  },
} as const;
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export function tx(key: keyof typeof copy.ru): string { return copy[language][key]; }
