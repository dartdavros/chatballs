import { copy as accepted } from '../agent-test/copy';

export const copy = {
  ru: {
    ...accepted.ru,
    title: 'Проверка агента · ожидание внешнего ответа',
    frame: 'S06 · Проверочная панель — ожидание внешнего ответа',
    reviewNote: 'Статический дизайн, S06-r1. Показано обычное ожидание после отправки одной примерной реплики. Реальный запрос не выполнялся; принятие внешним сервисом, его действия и доставка не проверялись.',
    proposal: 'На утверждение один кадр: сообщение клиента и ожидание ответа с общим индикатором. Ввод, повторная отправка и перезапуск недоступны. Закрытие панели не обещает остановку внешнего сервиса. Настройки и разрешения сохраняются как в принятом начальном кадре.',
    messageText: 'Здравствуйте! Как связаться с поддержкой?',
    waitingLabel: 'Ожидаем ответ внешнего агента',
    waitingHelp: 'Ответ ещё не получен.',
  },
  en: {
    ...accepted.en,
    title: 'Agent test · waiting for an external reply',
    frame: 'S06 · Agent test panel — waiting for an external reply',
    reviewNote: 'Static design, S06-r1. Ordinary waiting after sending one illustrative message. No real request was made; service acceptance, actions and delivery have not been verified.',
    proposal: 'One frame for approval: a client message and reply waiting with the shared indicator. Input, sending again and restart are unavailable. Closing the panel does not promise to stop the external service. Settings and permissions remain as in the accepted initial frame.',
    messageText: 'Hello! How can I contact support?',
    waitingLabel: 'Waiting for the external agent’s reply',
    waitingHelp: 'No reply has been received yet.',
  },
} as const;
export const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export function tx(key: keyof typeof copy.ru): string { return copy[language][key]; }
