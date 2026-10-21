(function () {
  const { h, text, card, line, actions, button, link, field, table, note } = window.ServiceParts;
  const U = window.ServiceUI;
  const data = window.ServiceSelectionData;
  window.ServiceCatalog = function () {
    const [search, setSearch] = window.React.useState('');
    const entries = data.adapters.filter(row => row.join(' ').toLowerCase().includes(search.toLowerCase()));
    return h('div', { className: 'si-card-body' },
      h(U.SearchInput, { placeholder: 'Найти адаптер', value: search, onChange: setSearch, clearable: true }),
      card('Установленные адаптеры', ...entries.map(([name, description]) => line(name, description,
        h(U.Button, { variant: 'secondary', onClick: () => window.ServiceShowFrame(name === 'MCP' ? 'C11' : 'C04') }, 'Выбрать'))),
        !entries.length && text('p', 'По этому запросу адаптеры не найдены.')),
      note('Нужного адаптера нет?', 'Обратитесь к администратору установки.'));
  };
  window.ServiceValuePicker = function () {
    const [source, setSource] = window.React.useState('Контекст');
    const [search, setSearch] = window.React.useState('');
    const [selected, setSelected] = window.React.useState('Диалог → Контакт → Имя');
    const entries = (data.values[source] || []).filter(row => row[0].toLowerCase().includes(search.toLowerCase()));
    return h('div', { className: 'si-card-body' },
      card('Значение параметра', h(U.SelectField, { label: 'Источник', value: source, options: data.sources.map(v => [v, v]),
        onChange: v => { setSource(v); setSelected(''); setSearch(''); } }),
        source === 'Постоянное значение' ? field('Значение', '', 'Будет одинаковым при каждом запуске.') : h(window.React.Fragment, null,
          h(U.SearchInput, { placeholder: 'Найти поле', value: search, onChange: setSearch, clearable: true }),
          table(['Поле', 'Тип', ''], entries.map(([path, type]) => [path, type,
            h('button', { type: 'button', className: 'link', onClick: () => setSelected(path) }, selected === path ? 'Выбрано' : 'Выбрать')]))),
        selected && line('Выбранное значение', `${source} → ${selected}`, link('Преобразовать значение')),
        actions(button('Применить значение', true, source !== 'Постоянное значение' && !selected), link('Отмена'))),
      note('Доступные поля', 'Показаны данные выбранного запуска и предыдущих шагов. Секреты подключения здесь недоступны.'));
  };
})();
