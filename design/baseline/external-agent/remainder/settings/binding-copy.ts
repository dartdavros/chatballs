export const bindingCopy = {
  ru: {
    add: 'Добавить связь', remove: 'Удалить связь', choose: 'Выберите агента',
    unselected: 'Агент не выбран', row: 'Связь', empty: 'Связей с агентами пока нет.',
    allBound: 'Все доступные агенты уже связаны с этим подключением.',
    addTitle: 'Добавить связь с агентом', addLead: 'Выберите существующего агента Chatballs и укажите его идентификатор во внешнем сервисе.',
    addConfirm: 'Добавить', cancel: 'Отмена', removeTitle: 'Удалить связь с агентом?',
    removeLead: 'Связь с этим агентом будет удалена. Изменение нужно сохранить в настройках.', removeConfirm: 'Удалить',
  },
  en: {
    add: 'Add binding', remove: 'Delete binding', choose: 'Choose an agent',
    unselected: 'No agent selected', row: 'Binding', empty: 'No agent bindings yet.',
    allBound: 'All available agents are already bound to this connection.',
    addTitle: 'Add an agent binding', addLead: 'Choose an existing Chatballs agent and enter its identifier in the external service.',
    addConfirm: 'Add', cancel: 'Cancel', removeTitle: 'Delete this agent binding?',
    removeLead: 'The binding for this agent will be deleted. Save this change in Settings.', removeConfirm: 'Delete',
  },
} as const;
const language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
export const bindingTx = (key: keyof typeof bindingCopy.ru): string => bindingCopy[language][key];
