import { copy as accepted } from '../agent-external/copy';

export const copy = {
  ru: {
    ...accepted.ru,
    title: 'Проверка агента · внешнее исполнение',
    frame: 'S05 · Проверочная панель — внешнее исполнение',
    reviewNote: 'Статический дизайн, S05-r1. Возможность включена; подключение, привязка и параметры агента подготовлены в настройках. Панель открыта до первой отправки. Реальные запросы, действия и доставка не выполняются.',
    proposal: 'На утверждение один кадр: внешняя проверка без разрешённых полей клиента. Предпросмотр действий заменён предупреждением о реальном запросе; язык, речь и основная карточка сохранены. На 320–390 px остаётся горизонтальная прокрутка текущего приложения.',
    panelSubtitle: 'Внешнее исполнение · Сервис поддержки',
    externalMode: 'Настоящее выполнение',
    externalTestWarning: 'Текст будет передан внешнему сервису. Запрос может запустить действия сервиса; безопасная имитация недоступна.',
    testDataEmpty: 'Передача полей клиента не разрешена. Проверка доступна без дополнительных данных.',
  },
  en: {
    ...accepted.en,
    title: 'Agent test · external execution',
    frame: 'S05 · Agent test panel — external execution',
    reviewNote: 'Static design, S05-r1. The feature is enabled; the connection, binding and agent settings are prepared in Settings. The panel is open before the first message. No real requests, actions or delivery take place.',
    proposal: 'One frame for approval: external testing without permitted client fields. The action preview is replaced by a real-request warning; language, speech and the main card are retained. At 320–390 px, the current application’s horizontal scrolling remains.',
    panelSubtitle: 'External execution · Support service',
    externalMode: 'Real execution',
    externalTestWarning: 'The text will be sent to the external service. The request may trigger service actions; a safe simulation is unavailable.',
    testDataEmpty: 'Sharing client fields is not permitted. Testing is available without additional data.',
  },
} as const;
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export function tx(key: keyof typeof copy.ru): string { return copy[language][key]; }
