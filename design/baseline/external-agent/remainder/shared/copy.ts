export const language=new URLSearchParams(location.search).get('lang')==='en'?'en':'ru';
export const copy={
  ru:{title:'Внешнее исполнение · оставшиеся макеты',review:'Статический дизайн на общую приёмку. Все данные, ответы, статусы и результаты — иллюстрации документа. API, внешние действия, доставка, ключи и согласия не выполняются.',
    width:'Ширина',theme:'Тема',language:'Язык',accent:'Акцент',light:'Светлая',dark:'Тёмная',
    gallery:'Все новые состояния',pending:'Ожидает личной приёмки',
    settings:'Настройки и разрешения',agents:'Карточка агента',tests:'Проверочная панель',chat:'Чат сотрудника',client:'Клиентский виджет и согласие'},
  en:{title:'External execution · remaining designs',review:'Static design for collective approval. All data, replies, statuses and results illustrate this document. No APIs, external actions, delivery, keys or consent operations take place.',
    width:'Width',theme:'Theme',language:'Language',accent:'Accent',light:'Light',dark:'Dark',
    gallery:'All new states',pending:'Awaiting owner approval',
    settings:'Settings and permissions',agents:'Agent card',tests:'Agent test panel',chat:'Employee chat',client:'Customer widget and consent'},
} as const;
export const tx=(key:keyof typeof copy.ru)=>copy[language][key];
