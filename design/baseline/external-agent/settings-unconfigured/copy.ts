import { copy as accepted } from '../settings-off/copy';

// S02-only proposed text; labels from the accepted shell remain unchanged.
export const copy = {
  ru: {
    ...accepted.ru,
    title: 'Внешнее исполнение включено · подключение не настроено',
    frame: 'S02 · Внешнее исполнение включено, подключение ещё не настроено',
    reviewNote: 'Статический дизайн, S02-r1. Включение, сохранение, проверка и создание ключа не выполняются. Не вводите реальные ключи.',
    proposal: 'На утверждение: включённая опция и пустая форма в принятом разделе настроек. Направления доступа разделены. Входящий ключ ещё не создан; его действие показано без результата. Другие состояния этим кадром не открываются.',
    externalHelp: 'Возможность включена. Настройте подключение ниже, чтобы агенты могли использовать внешний сервис.',
    connectionTitle: 'Подключение внешнего сервиса', notConfigured: 'Не настроено',
    connectionName: 'Название подключения', serviceUrl: 'HTTPS-адрес сервиса',
    outgoingTitle: 'Chatballs → внешний сервис', outgoingHelp: 'Доступ Chatballs к сервису, который исполняет агента.',
    outgoingKey: 'Ключ доступа к сервису', outgoingKeyHint: 'Используйте ключ, выданный вашим внешним сервисом.',
    incomingTitle: 'Внешний сервис → Chatballs', incomingHelp: 'Отдельный доступ к Chatballs для отправки ответов и запроса передачи диалога сотруднику.',
    keyAbsent: 'Ключ ещё не создан', createKey: 'Создать ключ',
    incomingKeyHint: 'Новый ключ создаётся только по вашему действию и показывается один раз. Сохранённый ключ при просмотре настроек не раскрывается.',
    saveConnection: 'Сохранить подключение', checkConnection: 'Проверить подключение',
    checkHint: 'Проверка читает возможности сервиса. Она не запускает агента и не отправляет сообщения.',
  },
  en: {
    ...accepted.en,
    title: 'External execution enabled · connection not configured',
    frame: 'S02 · External execution enabled, connection not configured',
    reviewNote: 'Static design, S02-r1. Enabling, saving, checking and key creation are inactive. Do not enter real keys.',
    proposal: 'For approval: the enabled option and an empty form in the accepted settings section. Access directions are separate. The incoming key has not been created; its action has no result. This frame does not open other states.',
    externalHelp: 'The option is enabled. Configure the connection below so agents can use the external service.',
    connectionTitle: 'External service connection', notConfigured: 'Not configured',
    connectionName: 'Connection name', serviceUrl: 'Service HTTPS address',
    outgoingTitle: 'Chatballs → external service', outgoingHelp: 'Chatballs access to the service that executes the agent.',
    outgoingKey: 'Service access key', outgoingKeyHint: 'Use the key issued by your external service.',
    incomingTitle: 'External service → Chatballs', incomingHelp: 'Separate access to Chatballs for submitting replies and asking to transfer the conversation to a staff member.',
    keyAbsent: 'Key not created yet', createKey: 'Create key',
    incomingKeyHint: 'A new key is created only through your explicit action and shown once. Viewing settings does not reveal a saved key.',
    saveConnection: 'Save connection', checkConnection: 'Check connection',
    checkHint: 'The check reads service capabilities. It does not run the agent or send messages.',
  },
} as const;
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export function tx(key: keyof typeof copy.ru): string { return copy[language][key]; }
