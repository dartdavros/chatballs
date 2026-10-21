(function () {
  const { h, text } = window.ServiceParts;
  const U = window.ServiceUI;
  function Canvas({ page, initialFrame }) {
    const query = new URLSearchParams(location.search);
    const [theme, setTheme] = window.React.useState(query.get('theme') || 'light');
    const [accent, setAccent] = window.React.useState(query.get('accent') || '#0f9b8e');
    const [width, setWidth] = window.React.useState(Number(query.get('width')) === 1024 ? 1024 : 1440);
    const journey = page === 'journey';
    const frames = journey ? window.ServiceFrames.journey() : Object.entries(window.ServiceFrames).filter(([key]) => key !== 'journey').flatMap(([,build]) => build());
    const [draft, setDraft] = window.React.useState(window.JourneyData?.defaultDraft || {});
    const [saved, setSaved] = window.React.useState(window.JourneyData?.defaultDraft || {});
    const [reviewNote, setReviewNote] = window.React.useState('');
    const [selected, setSelected] = window.React.useState(query.get('frame') || initialFrame || (journey ? 'J01' : { connections: 'C01', editor: 'E02', settings: 'P01' }[page]));
    window.ServiceShowFrame = setSelected;
    window.ServiceJourneyNotice = setReviewNote;
    window.React.useLayoutEffect(() => U.applyAppearance(theme === 'dark' ? 'DARK' : 'LIGHT', accent), [theme, accent]);
    window.ServiceNavigate = label => {
      const target = window.ServiceRoutes(selected, label);
      if (target) setSelected(target);
    };
    const select = (label, value, change, entries) => h('label', null, label,
      h('select', { value, onChange: e => change(e.target.value) }, ...entries.map(([v, title]) => h('option', { key: v, value: v }, title))));
    const board = h('div', { className: 'si-board' }, ...frames.filter(v => selected === 'all' || v.id === selected).map(item =>
      h(window.ServiceScreen, { key: item.id, item: journey && ['J03', 'J11'].includes(item.id) ? { ...item, heading: draft.connectionName }
        : journey && item.id==='J06' ? { ...item, heading: draft.scenarioName }
        : item.vendorName ? { ...item, heading: draft.vendors?.[item.vendorName]?.name || item.heading } : item, width })));
    return h(U.ConfigProvider, { theme: { algorithm: theme === 'dark' ? U.theme.darkAlgorithm : U.theme.defaultAlgorithm, token: { colorPrimary: accent } } },
      h('section', { className: 'si-canvas' },
        h('div', { className: 'si-review' }, text('h1', 'Chatballs · Подключения и сценарии'),
          text('p', journey ? 'Макеты Битрикс24, amoCRM и Mindbox. Значения — примеры; запросов к сервисам нет. Вводите только вымышленные секреты. Для Битрикс24: https://nord.example/rest/1/preview/. Исход OAuth выберите над макетом.' : 'Предыдущая версия отклонена. Эти кадры сохраняют перечень требований и ещё не переработаны под путь конкретного сервиса.'),
          select('Кадр', selected, setSelected, [['all', 'Все кадры'], ...frames.map(v => [v.id, `${v.id} · ${v.title}`])]),
          select('Ширина', width, v => setWidth(Number(v)), [['1440', '1440'], ['1024', '1024']]),
          select('Тема', theme, setTheme, [['light', 'Светлая'], ['dark', 'Тёмная']]),
          select('Акцент', accent, setAccent, U.ACCENT_PRESETS),
          ...(journey ? [['J01', 'Начать путь'], ['J03', 'После подключения'], ['J04', 'Настройка'], ['J06', 'Копия пресета'], ['X01', 'Свой сценарий'], ['Y15','Хранение']] : [['C01', 'Подключения'], ['E02', 'Редактор'], ['P01', 'Доступ и состояния']]).map(([key, label]) =>
            h('button', { key, className: 'link', onClick: () => setSelected(key) }, label)),
          reviewNote && h('p', { role: 'status' }, reviewNote)),
        journey && selected === 'Q02' && h('div', { className: 'si-review' }, ...[['Q03', 'Показать успешный возврат'], ['Q07', 'Показать отказ'], ['Q08', 'Показать устаревший возврат']].map(([id, label]) =>
          h('button', { key: id, className: 'link', onClick: () => setSelected(id) }, label))),
        journey ? h(window.Journey.Context.Provider, { value: { draft, update: patch => setDraft(old => window.ConnectionDrafts.update(old,patch)),
          selectConnection:(id,name)=>{setDraft(old=>window.ConnectionDrafts.select(old,id,name));setSelected('J03');},
          beginConnection:()=>{setDraft(old=>window.ConnectionDrafts.begin(old));setSelected('J02');},
          save: (patch = {}) => { const next = { ...draft, ...patch }; setSaved(next); setDraft(next); }, discard: () => setDraft(saved),
          go: id => { setReviewNote(''); setSelected(id); }, notify: setReviewNote } }, h(window.Custom.Provider, null, board)) : board));
  }
  window.ServiceCanvas = Canvas;
  window.ServiceFrames = {};
})();
