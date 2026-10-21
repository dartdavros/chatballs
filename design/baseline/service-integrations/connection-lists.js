// Design content only. Existing connection groups render the unchanged ConnectionsTable.
(function () {
  const { h, text } = window.ServiceParts;
  const U = window.ServiceUI;
  const go = label => () => window.ServiceNavigate(label);
  const existing = (name, provider, extra = {}) => ({ id: name, name, provider,
    kind: provider === 'MCP' ? 'EXTERNAL_SERVER' : 'MESSENGER', config: {},
    isActive: true, status: 'OK', lastCheckedAt: null, lastError: '', channel: null, ...extra });
  window.ExistingConnections = ({ servers }) => h(U.ConnectionsTable, {
    items: servers
      ? [existing('Магазин', 'MCP', { externalServer: { type: 'mcp', url: 'https://api.example.org/mcp', tools: [] } })]
      : [existing('Поддержка сайта', 'WEB', { channel: { id: 1, name: 'Поддержка сайта', hasAgent: true } }),
        existing('Почта поддержки', 'EMAIL', { config: { email: 'support@example.org' } })],
    testingId: null, onTest: go('Проверить'), onEdit: () => {}, onToggleActive: () => {}, onDelete: () => {},
  });
  const services = [
    { name: 'Магазин · основной', provider: 'HTTP', adapter: 'HTTP / API', scenarios: '2 сценария', status: 'Подключено', tone: 'success', hint: 'Доступ проверен', isActive: true },
    { name: 'Магазин · склад', provider: 'HTTP', adapter: 'HTTP / API', scenarios: '1 сценарий', status: 'Доступ истёк', tone: 'error', hint: 'Восстановите доступ', isActive: true },
    { name: 'Каталог поставщика', provider: 'MCP', adapter: 'MCP', scenarios: 'Нет сценариев', status: 'Выключено', tone: 'neutral', hint: 'Действия остановлены', isActive: false },
  ];
  window.ServiceConnectionList = function () {
    return h('div', { className: 'table-card' }, h('table', { className: 'baseline-table integrations-connections-table' },
      h('thead', null, h('tr', null, ...['Название', 'Сценарии', 'Статус', ''].map((v, i) => h('th', { key: i }, v)))),
      h('tbody', null, ...services.map(item => h('tr', { key: item.name },
        h('td', null, h('div', { className: 'product-cell' }, h(U.ConnectionIcon, { provider: item.provider }), h('span', null,
          h('button', { className: 'link is-strong', title: item.name, onClick: go(item.name) }, item.name), text('small', item.adapter)))),
        h('td', null, text('span', item.scenarios, 'integration-tools-count')),
        h('td', null, h('div', { className: 'integration-status' }, h(U.ToneBadge, {
          bg: item.tone === 'neutral' ? 'var(--n-9)' : `var(--${item.tone}-bg)`,
          color: item.tone === 'neutral' ? 'var(--n-4)' : `var(--${item.tone}-text)`,
        }, item.status), text('small', item.hint))),
        h('td', { className: 'row-actions' }, h(U.RowActions, { integration: { ...item, kind: 'EXTERNAL_SERVER' }, testing: false,
          onTest: go('Проверить'), onEdit: go(item.name), onToggleActive: go('Выключить подключение'), onDelete: go('Удалить подключение') })))))));
  };
})();
