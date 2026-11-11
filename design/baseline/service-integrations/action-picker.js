(() => {
  const root = document.getElementById('cb-action-preview');
  if (!root) return;
  const picker = root.querySelector('#cb-picker');
  const tree = root.querySelector('#cb-action-tree');
  const search = root.querySelector('#cb-action-search');
  const clearButton = root.querySelector('#cb-clear-search');
  const empty = root.querySelector('#cb-search-empty');
  const status = root.querySelector('#cb-catalog-status');
  const panel = root.querySelector('#cb-parameters');
  const closed = root.querySelector('#cb-closed');
  const form = root.querySelector('#cb-parameter-form');
  const complete = root.querySelector('#cb-demo-complete');
  const fields = root.querySelector('#cb-parameter-fields');
  const heading = root.querySelector('#cb-parameter-title');
  const path = root.querySelector('#cb-selection-path');
  const plan = root.querySelector('#cb-plan-text');
  const selectedStatus = root.querySelector('#cb-selection-status');
  const groupData = [
    { id: 'bitrix-sales', title: 'Битрикс24', subtitle: 'Отдел продаж', icon: 'plug', children: [
      { id: 'bitrix-sales-crm', title: 'CRM', children: [
        { id: 'sales-lead-create', title: 'Добавить лида', kind: 'operation', profile: 'lead' },
        { id: 'sales-lead-update', title: 'Обновить лида', kind: 'operation', profile: 'update' },
        { id: 'sales-contact-find', title: 'Найти контакт', kind: 'operation', profile: 'find' },
        { id: 'sales-deal-create', title: 'Создать сделку', kind: 'operation', profile: 'deal' }
      ] },
      { id: 'bitrix-sales-users', title: 'Пользователи', children: [
        { id: 'sales-user-find', title: 'Найти пользователя', kind: 'operation', profile: 'user' }
      ] }
    ] },
    { id: 'bitrix-shop', title: 'Битрикс24', subtitle: 'Интернет-магазин', icon: 'plug', children: [
      { id: 'bitrix-shop-crm', title: 'CRM', children: [
        { id: 'shop-lead-create', title: 'Добавить лида', kind: 'operation', profile: 'lead' },
        { id: 'shop-contact-create', title: 'Добавить контакт', kind: 'operation', profile: 'contact' },
        { id: 'shop-deal-create', title: 'Создать сделку', kind: 'operation', profile: 'deal' }
      ] },
      { id: 'bitrix-shop-users', title: 'Пользователи', children: [
        { id: 'shop-user-find', title: 'Найти пользователя', kind: 'operation', profile: 'user' }
      ] }
    ] },
    { id: 'scenarios', title: 'Сценарии', icon: 'workflow', children: [
      { id: 'scenarios-sales', title: 'Продажи', children: [
        { id: 'scenario-qualify', title: 'Квалифицировать обращение', kind: 'scenario', profile: 'qualify' },
        { id: 'scenario-proposal', title: 'Подготовить предложение', kind: 'scenario', profile: 'proposal' },
        { id: 'scenario-manager', title: 'Назначить менеджера', kind: 'scenario', profile: 'assign' }
      ] },
      { id: 'scenarios-support', title: 'Поддержка', children: [
        { id: 'scenario-register', title: 'Зарегистрировать обращение', kind: 'scenario', profile: 'register' },
        { id: 'scenario-escalate', title: 'Передать обращение специалисту', kind: 'scenario', profile: 'assign' }
      ] },
      { id: 'scenarios-none', title: 'Без категории', children: [
        { id: 'scenario-check', title: 'Проверить данные клиента', kind: 'scenario', profile: 'check' }
      ] }
    ] }
  ];
  const actions = new Map();
  function indexItems(nodes, ancestors = []) {
    for (const node of nodes) {
      if (node.children) indexItems(node.children, [...ancestors, node]);
      else actions.set(node.id, { ...node, ancestors, source: ancestors[0], category: ancestors.slice(1).map(item => item.title).join(' / ') });
    }
  }
  indexItems(groupData);
  const defaultExpanded = ['bitrix-sales', 'bitrix-sales-crm'];
  const expanded = new Set(defaultExpanded);
  const searchCollapsed = new Set();
  let query = '';
  let selected = null;
  const normalize = text => String(text).toLocaleLowerCase('ru').replaceAll('ё', 'е').trim();
  const escape = text => String(text).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const icon = (name, className = '') => `<i data-lucide="${name}" class="${className}" aria-hidden="true"></i>`;
  const typeTitle = item => item.kind === 'scenario' ? 'Сценарий' : 'Операция';
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons({ attrs: { width: 16, height: 16 } }); }
  function plural(count, forms) { const n = count % 100; return forms[n >= 11 && n <= 14 ? 2 : count % 10 === 1 ? 0 : count % 10 >= 2 && count % 10 <= 4 ? 1 : 2]; }
  function highlight(text) {
    const words = query.split(/\s+/).filter(Boolean).sort((a, b) => b.length - a.length);
    if (!words.length) return escape(text);
    const pattern = words.map(word => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    const matcher = new RegExp(`(${pattern})`, 'giu');
    return String(text).split(matcher).map((part, index) => index % 2 ? `<mark>${escape(part)}</mark>` : escape(part)).join('');
  }
  function matches(node) {
    const item = actions.get(node.id);
    const haystack = normalize([item.title, typeTitle(item), ...item.ancestors.flatMap(parent => [parent.title, parent.subtitle || ''])].join(' '));
    return !query || query.split(/\s+/).every(word => haystack.includes(word));
  }
  function filterTree(nodes) {
    return nodes.flatMap(node => {
      if (!node.children) return matches(node) ? [{ ...node, count: 1 }] : [];
      const children = filterTree(node.children);
      return children.length ? [{ ...node, children, count: children.reduce((sum, child) => sum + child.count, 0) }] : [];
    });
  }
  function actionMarkup(node) {
    const item = actions.get(node.id);
    const caption = item.kind === 'scenario' ? `Сценарий · ${item.category}` : `Операция · ${item.source.subtitle}`;
    return `<li><button type="button" class="cb-action cursor-interaction" data-action="${item.id}">${icon(item.kind === 'scenario' ? 'workflow' : 'plug', 'cb-action-symbol')}<span class="cb-action-copy"><span class="cb-action-title">${highlight(item.title)}</span><span class="cb-action-caption">${highlight(caption)}</span></span>${icon('chevron-right', 'cb-action-arrow')}</button></li>`;
  }
  function groupMarkup(node, depth) {
    if (!node.children) return actionMarkup(node);
    const isOpen = query ? !searchCollapsed.has(node.id) : expanded.has(node.id);
    const childrenId = `cb-group-${node.id}`;
    const symbol = depth === 0 ? `<span class="cb-group-symbol">${icon(node.icon)}</span>` : icon(isOpen ? 'folder-open' : 'folder', 'cb-action-symbol');
    const subtitle = node.subtitle ? `<span class="cb-group-subtitle">${highlight(node.subtitle)}</span>` : '';
    return `<li${depth === 0 ? ' class="cb-root"' : ''}><button type="button" class="cb-group-button ${depth === 0 ? 'cb-group-root ' : ''}cursor-interaction" data-group="${node.id}" aria-expanded="${isOpen}" aria-controls="${childrenId}">${icon('chevron-right', 'cb-chevron')}${symbol}<span class="cb-group-label">${highlight(node.title)}${subtitle}</span><span class="cb-count" aria-label="${node.count} ${plural(node.count, ['действие', 'действия', 'действий'])}">${node.count}</span></button><ul id="${childrenId}" class="cb-children"${isOpen ? '' : ' hidden'}>${isOpen ? node.children.map(child => groupMarkup(child, depth + 1)).join('') : ''}</ul></li>`;
  }
  function renderCatalog() {
    const visible = filterTree(groupData);
    const count = visible.reduce((sum, node) => sum + node.count, 0);
    tree.innerHTML = visible.map(node => groupMarkup(node, 0)).join('');
    tree.hidden = count === 0;
    empty.hidden = count !== 0;
    clearButton.hidden = search.value.length === 0;
    root.querySelector('#cb-search-shortcut').hidden = search.value.length > 0;
    status.textContent = `${query ? 'Найдено' : 'Доступно'} ${count} ${plural(count, ['действие', 'действия', 'действий'])}`;
    refreshIcons();
  }
  const inputField = (name, label, value, required = true) => `<label class="cb-field"><span class="cb-field-label">${escape(label)}${required ? '' : '<span class="cb-field-note">необязательно</span>'}</span><input name="${name}" class="cb-input" value="${escape(value)}"${required ? ' required' : ''}></label>`;
  const selectField = (name, label, options) => `<label class="cb-field"><span class="cb-field-label">${escape(label)}</span><select name="${name}" class="cb-input">${options.map(option => `<option>${escape(option)}</option>`).join('')}</select></label>`;
  const commentField = () => '<label class="cb-field"><span class="cb-field-label">Комментарий<span class="cb-field-note">необязательно</span></span><textarea name="comment" class="cb-input" rows="3" placeholder="Дополнительная информация"></textarea></label>';
  const personField = () => selectField('responsible', 'Ответственный', ['Алексей Морозов', 'Мария Волкова']);
  function parameterConfig(item) {
    const source = item.source.subtitle;
    switch (item.profile) {
      case 'lead': return { fields: inputField('title', 'Название лида', 'Обращение Ирины Соколовой') + personField() + commentField(), plan: `Создаст лида в Битрикс24 «${source}» и свяжет его с текущим диалогом.` };
      case 'update': return { fields: selectField('lead', 'Лид', ['№1842 · Обращение Ирины Соколовой']) + selectField('status', 'Статус', ['В работе', 'Новый', 'Обработан']) + commentField(), plan: `Обновит выбранного лида в Битрикс24 «${source}».` };
      case 'find': return { fields: inputField('query', 'Имя или телефон', 'Ирина Соколова'), plan: `Найдёт контакты в Битрикс24 «${source}». Данные контактов не изменятся.` };
      case 'contact': return { fields: inputField('name', 'Имя контакта', 'Ирина Соколова') + inputField('email', 'Электронная почта', 'irina@example.com', false) + personField(), plan: `Создаст контакт в Битрикс24 «${source}».` };
      case 'deal': return { fields: inputField('title', 'Название сделки', 'Обращение из чата') + personField() + commentField(), plan: `Создаст сделку в Битрикс24 «${source}».` };
      case 'user': return { fields: inputField('query', 'Имя сотрудника', 'Алексей'), plan: `Найдёт пользователей Битрикс24 «${source}». Данные пользователей не изменятся.` };
      case 'qualify': return { fields: selectField('interest', 'Интерес клиента', ['Консультация', 'Покупка', 'Продление']) + personField() + commentField(), plan: 'Сохранит результат квалификации и назначит ответственного за обращение.' };
      case 'proposal': return { fields: inputField('title', 'Тема предложения', 'Предложение для Ирины Соколовой') + commentField(), plan: 'Подготовит предложение на основе текущего обращения.' };
      case 'assign': return { fields: personField() + commentField(), plan: 'Передаст обращение выбранному сотруднику и добавит комментарий.' };
      case 'register': return { fields: inputField('title', 'Тема обращения', 'Вопрос Ирины Соколовой') + selectField('priority', 'Приоритет', ['Обычный', 'Высокий']) + commentField(), plan: 'Зарегистрирует обращение и свяжет его с текущим диалогом.' };
      default: return { fields: inputField('name', 'Имя клиента', 'Ирина Соколова'), plan: 'Проверит заполнение данных клиента в текущем диалоге.' };
    }
  }
  function selectAction(id) {
    selected = actions.get(id);
    if (!selected) return;
    const config = parameterConfig(selected);
    heading.textContent = selected.title;
    root.querySelector('#cb-parameter-kind').textContent = typeTitle(selected);
    path.textContent = selected.ancestors.map(node => node.subtitle ? `${node.title} · ${node.subtitle}` : node.title).join(' / ');
    fields.innerHTML = config.fields;
    plan.textContent = config.plan;
    picker.hidden = true;
    closed.hidden = true;
    panel.hidden = false;
    form.hidden = false;
    complete.hidden = true;
    selectedStatus.textContent = `Выбрано: ${selected.title}. ${path.textContent}.`;
    refreshIcons();
    fields.querySelector('input, select, textarea')?.focus({ preventScroll: true });
  }
  function showCatalog(reset = false) {
    if (reset) {
      search.value = '';
      query = '';
      expanded.clear();
      defaultExpanded.forEach(id => expanded.add(id));
      searchCollapsed.clear();
      selected = null;
    }
    panel.hidden = true;
    closed.hidden = true;
    picker.hidden = false;
    renderCatalog();
    const previous = selected ? tree.querySelector(`[data-action="${selected.id}"]`) : null;
    (previous || search).focus({ preventScroll: true });
  }
  function closeSurface() {
    picker.hidden = true;
    panel.hidden = true;
    closed.hidden = false;
    root.querySelector('#cb-reopen').focus({ preventScroll: true });
  }
  function clearSearch() {
    search.value = '';
    query = '';
    searchCollapsed.clear();
    renderCatalog();
    search.focus({ preventScroll: true });
  }
  root.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || !root.contains(button)) return;
    if (button.hasAttribute('data-group')) {
      const id = button.dataset.group;
      const set = query ? searchCollapsed : expanded;
      set.has(id) ? set.delete(id) : set.add(id);
      renderCatalog();
      tree.querySelector(`[data-group="${id}"]`)?.focus({ preventScroll: true });
    } else if (button.hasAttribute('data-action')) selectAction(button.dataset.action);
    else if (button.hasAttribute('data-close')) closeSurface();
    else if (button.hasAttribute('data-back')) showCatalog();
    else if (button.id === 'cb-reopen') showCatalog(true);
    else if (button.id === 'cb-clear-search' || button.id === 'cb-empty-clear') clearSearch();
  });
  search.addEventListener('input', () => { query = normalize(search.value); searchCollapsed.clear(); renderCatalog(); });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!selected || !form.reportValidity()) return;
    form.hidden = true;
    complete.hidden = false;
    root.querySelector('#cb-result-action').textContent = `${selected.title} · ${selected.source.subtitle || selected.category}`;
    selectedStatus.textContent = 'Демонстрация запуска. Внешние запросы не отправлялись.';
    complete.querySelector('button').focus({ preventScroll: true });
    refreshIcons();
  });
  root.addEventListener('keydown', event => {
    if (event.key === 'Tab' && !picker.hidden) {
      const controls = [...picker.querySelectorAll('button:not([disabled]), input:not([disabled])')].filter(control => !control.closest('[hidden]'));
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
      return;
    }
    if (event.key !== 'Escape') return;
    event.preventDefault();
    if (!panel.hidden) showCatalog();
    else if (!picker.hidden) closeSurface();
  });
  renderCatalog();
  search.focus({ preventScroll: true });
})();