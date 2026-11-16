import { language } from './copy';

export const helpCopy = {
  ru: {
    about: 'Подробнее: ', close: 'Понятно', example: 'Пример сообщения для клиента', openMessage: 'Открыть сообщение',
    externalTitle: 'Внешнее исполнение', externalText: 'Ответы готовит агент в отдельном внешнем сервисе. Chatballs передаёт ему обращение, получает результат и отправляет ответ клиенту. Подключение и доступы настраиваются здесь; в карточке агента выбирается готовое исполнение.',
    bindingsTitle: 'Связи с агентами', bindingsText: 'Связь указывает, какому агенту внешнего сервиса передавать обращения выбранного агента Chatballs. Внешний идентификатор берётся из этого сервиса. Одно подключение может обслуживать несколько агентов; доступ к данным и сообщениям разрешается для каждого отдельно.',
    processingTitle: 'Сроки обработки', processingText: 'Обычный запрос — срок ожидания стандартного ответа. Долгая обработка — срок для задач, которым нужно больше времени. Максимальное ожидание ограничивает допустимый срок любого запроса. Срок выбирается до отправки; статус «обрабатывается» не продлевает его. По истечении срока диалог передаётся сотруднику.',
    initiativeTitle: 'Инициативные сообщения', initiativeText: 'Это сообщения, которые внешний агент отправляет сам, без нового вопроса клиента — например, когда появился результат ранее обсуждённой задачи. Разрешение действует только для выбранного агента и подключения, в открытом диалоге под управлением ИИ. При активном или ожидающем обращении клиента отправка недоступна.',
    dataTitle: 'Доступ к данным', dataText: 'Внешний сервис получает исходный текст обращения. Дополнительно можно разрешить передачу отдельных полей контакта. Разрешения действуют только для выбранного агента и подключения; доступ встроенной модели на внешний сервис не переносится.',
    webFieldsTitle: 'Кастомные поля WEB-подключений', webFieldsText: 'Это дополнительные поля, настроенные для чата на сайте: например, город или тариф клиента. Поле относится к конкретному подключению чата на сайте. Два поля «Город» из разных подключений считаются разными и разрешаются отдельно.',
    templatesTitle: 'Оформленные сообщения', templatesText: 'Это заранее подготовленные сообщения с оформлением: например, карточка статуса заказа с номером, статусом и сроком доставки. Внешний агент подставляет данные только в разрешённый шаблон. В каналах, где такое оформление недоступно, используется текстовая версия.',
    capabilityTitle: 'Проверка подключения', capabilityText: 'Проверка показывает, доступен ли внешний сервис, принимает ли он ключ и поддерживает ли нужные возможности. Успешная проверка подключения не заменяет проверку поведения агента: её можно выполнить из карточки агента.',
    keysTitle: 'Ключи доступа', keysText: 'Ключ внешнего сервиса позволяет Chatballs передавать ему обращения. Ключ Chatballs позволяет сервису возвращать результаты в Chatballs. Это разные направления доступа. Замена делает прежний ключ недействительным, отзыв прекращает доступ по ключу.',
    greeting: 'Здравствуйте! Я помощник поддержки. Расскажите, с чем нужна помощь.',
    greetingTitle: 'Приветствие', orderTitle: 'Статус заказа',
  },
  en: {
    about: 'About: ', close: 'Got it', example: 'Example customer message', openMessage: 'Open message',
    externalTitle: 'External execution', externalText: 'An agent in a separate external service prepares replies. Chatballs sends it the request, receives the result and delivers the reply to the customer. Configure the connection and access here, then select the prepared execution in the agent card.',
    bindingsTitle: 'Agent bindings', bindingsText: 'A binding identifies which external-service agent receives requests from the selected Chatballs agent. Get the external identifier from that service. One connection can serve several agents; data and message permissions are granted separately for each.',
    processingTitle: 'Processing durations', processingText: 'Normal request is the time allowed for a standard reply. Long processing is the time allowed for tasks that need longer. Maximum wait limits the permitted duration of any request. The deadline is selected before sending; a processing status does not extend it. When it expires, the conversation goes to an employee.',
    initiativeTitle: 'Proactive messages', initiativeText: 'These are messages the external agent sends by itself, without a new customer question — for example, when a previously discussed task has a result. Permission applies only to the selected agent and connection, in an open conversation under AI control. Sending is unavailable while a customer request is active or waiting.',
    dataTitle: 'Data access', dataText: 'The external service receives the original request text. You can also permit specific contact fields. Permissions apply only to the selected agent and connection; built-in model access is not inherited by the external service.',
    webFieldsTitle: 'Custom fields from WEB connections', webFieldsText: 'These are additional fields configured for a website chat, such as the customer’s city or plan. Each field belongs to a specific website-chat connection. Two City fields from different connections are separate and require separate permission.',
    templatesTitle: 'Prepared messages', templatesText: 'These are predesigned messages, such as an order-status card with the order number, status and delivery date. The external agent supplies data only to an explicitly permitted template. Channels that do not support this presentation use its text version.',
    capabilityTitle: 'Connection check', capabilityText: 'The check shows whether the external service is reachable, accepts the key and supports the required capabilities. A successful connection check does not replace testing agent behavior, which is available in the agent card.',
    keysTitle: 'Access keys', keysText: 'The external service key allows Chatballs to send it requests. The Chatballs key allows the service to return results to Chatballs. These are different directions of access. Replacing a key invalidates its predecessor; revoking a key ends access through it.',
    greeting: 'Hello! I am the support assistant. Tell me what you need help with.',
    greetingTitle: 'Greeting', orderTitle: 'Order status',
  },
};
export const ht = (key: keyof typeof helpCopy.ru) => helpCopy[language][key];
export const helpTopics = {
  external: ['externalTitle', 'externalText'], bindings: ['bindingsTitle', 'bindingsText'],
  processing: ['processingTitle', 'processingText'], initiative: ['initiativeTitle', 'initiativeText'],
  data: ['dataTitle', 'dataText'], webFields: ['webFieldsTitle', 'webFieldsText'],
  templates: ['templatesTitle', 'templatesText'], capability: ['capabilityTitle', 'capabilityText'], keys: ['keysTitle', 'keysText'],
} as const;
export type HelpTopic = keyof typeof helpTopics;
