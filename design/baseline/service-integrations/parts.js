// Composition helpers for design frames. Controls are imported from internal-ui.
(function () {
  const h = (...args) => window.React.createElement(...args);
  const U = window.ServiceUI;
  const text = (tag, value, className = '') => h(tag, { className }, value);
  const button = (label, primary = false, disabled = false) => h(U.Button, {
    variant: primary ? 'primary' : 'secondary', disabled,
    onClick: () => window.ServiceNavigate?.(label),
  }, label);
  const link = label => h('button', { className: 'link', type: 'button', onClick: () => window.ServiceNavigate?.(label) }, label);
  const badge = (value, tone = 'neutral') => h(U.StatusPill, {
    status: { ok: 'healthy', error: 'error', warn: 'pending', accent: 'invited', neutral: 'unchecked' }[tone], label: value,
  });
  const note = (title, body, tone = 'info') => tone === 'info'
    ? h('p', { className: 'settings-section-note si-note' }, h('strong', null, title), body && ` ${body}`)
    : h('div', { className: `server-warning si-notice ${tone}` }, h(U.Icon, { name: tone === 'ok' ? 'check' : 'errorCircle', size: 16 }),
      h('p', null, h('strong', null, title), body && ` ${body}`));
  function Field({ label, value, help, kind, options }) {
    const [current, setCurrent] = window.React.useState(value);
    const props = { label, value: current, onChange: next => {
      setCurrent(next);
      if (options.frames?.[next]) window.ServiceShowFrame(options.frames[next]);
    }, disabled: options.disabled, wide: options.wide };
    const binding = kind === 'text' && /→|^(Ввод|Контекст|Событие|Шаг \d)\b/.test(value);
    const control = binding
      ? h('div', { className: `readonly-field select-like ${options.error ? 'is-invalid' : ''}` }, text('span', label),
        h('button', { className: 'select-box', type: 'button', 'aria-invalid': !!options.error, onClick: () => window.ServiceNavigate('Выбрать значение') },
          text('span', value, 'select-value'), h(U.Icon, { name: 'chevron', size: 14, strokeWidth: 2.2 })),
        options.error && h('small', { className: 'form-field-error', role: 'alert' }, options.error))
      : kind === 'select'
      ? h(U.SelectField, { ...props, invalid: !!options.error, options: (options.choices || [value]).map(v => [v, v]) })
      : kind === 'area' ? h(U.TextAreaField, props)
        : kind === 'file' ? h('div', { className: 'readonly-field' }, text('span', label), button(value))
          : h(U.FormField, { ...props, type: kind, error: options.error });
    return h('div', { className: `si-field ${options.wide ? 'wide' : ''}` }, control,
      help && text('small', help, 'si-field-help'));
  }
  const field = (label, value, help = '', kind = 'text', options = {}) => h(Field, { label, value, help, kind, options });
  const fields = (...children) => h('div', { className: 'server-two-fields si-fields' }, ...children);
  const actions = (...children) => h('div', { className: 'server-actions si-actions' }, ...children);
  const card = (title, ...children) => !title && children.length === 1
    ? children[0]
    : h('section', { className: 'administration-card si-card' }, title && text('h3', title), h('div', { className: 'si-card-body' }, ...children));
  const line = (name, description, trailing) => h('div', { className: 'si-line' }, h('div', { className: 'si-line-main' },
    text('strong', name), description && text('p', description)), trailing);
  const table = (heads, rows) => h('div', { className: 'table-card si-table-wrap' }, h('table', { className: 'baseline-table' },
    h('thead', null, h('tr', null, ...heads.map((v, i) => h('th', { key: i, className: !v ? 'si-table-actions' : undefined }, v)))),
    h('tbody', null, ...rows.map((row, i) => h('tr', { key: i }, ...row.map((v, j) => h('td', { key: j, className: !heads[j] ? 'si-table-actions' : undefined }, v)))))));
  const tabs = (values, active) => h(U.UnderlineTabs, { className: 'integrations-tabs si-tabs', items: values.map(key => ({ key, label: key })), value: active,
    onChange: value => window.ServiceNavigate?.(value) });
  const chips = (...values) => h('div', { className: 'si-chips' }, ...values.map(v => text('span', v, 'si-value-chip')));
  function Toggle({ label, help, on }) {
    const [checked, setChecked] = window.React.useState(on);
    return h('div', { className: 'server-enabled' }, h('span', null, text('strong', label), text('small', help)),
      h(U.SwitchButton, { className: 'ui-switch', label, checked, onClick: () => setChecked(!checked) }));
  }
  const toggle = (label, help, on = true) => h(Toggle, { label, help, on });
  const block = (number, title, summary, ...children) => h('section', { className: 'si-block' },
    h('header', null, text('span', number, 'si-step-number'), h('div', null, text('h3', title), text('p', summary)), link('Изменить')),
    children.length > 0 && h('div', { className: 'si-block-body' }, ...children));
  const frame = (id, title, heading, lead, content, options = {}) => ({ id, title, heading, lead, content, ...options });
  window.ServiceParts = { h, text, button, link, badge, note, field, fields, actions, card, line, table, tabs, chips, toggle, block, frame };
})();
