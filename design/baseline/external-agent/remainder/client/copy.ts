export const clientCopy = {
  ru: {
    title: 'Помощник',
    greeting: 'Здравствуйте! Готов помочь и ответить на вопросы. Чем можем помочь?',
    formTitle: 'Представьтесь, чтобы мы могли ответить на ваше обращение',
    originalConsent: 'Продолжая, вы соглашаетесь на обработку сообщений для ответа на обращение.',
    proposedConsent: '<p>Продолжая, вы соглашаетесь на обработку сообщений для ответа на обращение.</p><p>Для подготовки ответа текст ваших сообщений и поля клиента, передачу которых разрешила организация, передаются во внешний сервис «Сервис поддержки» в исходном виде.</p><p>Из голосового сообщения внешнему сервису передаётся текст после распознавания в Chatballs. Исходная аудиозапись этому сервису не передаётся.</p>',
  },
  en: {
    title: 'Assistant',
    greeting: 'Hello! Happy to help and answer your questions. What can we do for you?',
    formTitle: 'Introduce yourself so that we can answer your request',
    originalConsent: 'By continuing you agree that your messages are processed to answer your request.',
    proposedConsent: '<p>By continuing you agree that your messages are processed to answer your request.</p><p>To prepare a reply, the text of your messages and the customer fields that the organization has permitted for sharing are sent in their original form to the external service “Support service”.</p><p>For a voice message, the external service receives the text after transcription in Chatballs. The original audio recording is not sent to this service.</p>',
  },
} as const;

export function clientLanguage(): 'ru' | 'en' {
  return new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
}

export function clientText(key: keyof typeof clientCopy.ru): string {
  return clientCopy[clientLanguage()][key];
}
