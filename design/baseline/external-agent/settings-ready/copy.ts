import { copy as accepted } from '../settings-unconfigured/copy';

export const copy = {
  ru: {
    ...accepted.ru,
    title: 'Внешнее исполнение · подключение готово',
    frame: 'S03 · Внешнее исполнение настроено — подключение готово',
    reviewNote: 'Статический дизайн, S03-r1. Адрес, настройки и результат проверки — примеры состояния. Реальная интеграция не проверялась; ключи и действия с ними не используются.',
    proposal: 'На утверждение: сохранённое подключение, два скрытых ключа и успешная проверка возможностей. Готовность подключения не означает, что агенты уже переключены или сообщения доставлены. Другие состояния не открываются.',
    externalHelp: 'Подключение настроено. Внешнее исполнение можно выбрать у агента после настройки его привязки и разрешений.',
    connectionNameValue: 'Сервис поддержки', serviceUrlValue: 'https://agent.example',
    connectionReady: 'Подключение готово', incomingKey: 'Ключ доступа к Chatballs',
    outgoingStored: 'Ключ сохранён и скрыт. Для замены используйте ключ, выданный внешним сервисом.',
    incomingStored: 'Ключ создан и скрыт. Полное значение сохранённого ключа повторно не показывается.',
    replaceKey: 'Заменить ключ', replaceShort: 'Заменить', revokeShort: 'Отозвать',
    revokeHint: 'Замена или отзыв этого ключа прекратит доступ внешнего сервиса по прежнему ключу.',
    checkTitle: 'Проверка подключения', compatibility: 'Совместим', capabilitiesSummary: 'Сервис доступен, версия и обязательные возможности совместимы.',
    formats: 'Ответы сервиса: текст, изображения, файлы, контакты и запрос контакта, оформленные сообщения.',
    channelLimits: 'Доступные клиенту форматы зависят от канала. Оформленные сообщения используют только разрешённые агенту шаблоны.',
  },
  en: {
    ...accepted.en,
    title: 'External execution · connection ready',
    frame: 'S03 · External execution configured — connection ready',
    reviewNote: 'Static design, S03-r1. The address, settings and check result illustrate this state. No real integration has been verified; keys and key actions are inactive.',
    proposal: 'For approval: a saved connection, two hidden keys and a successful capability check. Connection readiness does not mean agents have switched or messages have been delivered. Other states are not opened.',
    externalHelp: 'The connection is configured. An agent can select external execution once its binding and permissions are configured.',
    connectionNameValue: 'Support service', serviceUrlValue: 'https://agent.example',
    connectionReady: 'Connection ready', incomingKey: 'Chatballs access key',
    outgoingStored: 'The key is saved and hidden. To replace it, use a key issued by the external service.',
    incomingStored: 'The key has been created and is hidden. A saved key is not shown in full again.',
    replaceKey: 'Replace key', replaceShort: 'Replace', revokeShort: 'Revoke',
    revokeHint: 'Replacing or revoking this key ends the external service’s access through the previous key.',
    checkTitle: 'Connection check', compatibility: 'Compatible', capabilitiesSummary: 'The service is available; its version and required capabilities are compatible.',
    formats: 'Service replies: text, images, files, contacts and contact requests, formatted messages.',
    channelLimits: 'Customer formats depend on the channel. Formatted messages use only templates explicitly allowed for the agent.',
  },
} as const;
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export function tx(key: keyof typeof copy.ru): string { return copy[language][key]; }
