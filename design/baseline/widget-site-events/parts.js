(function () {
  const h = window.React.createElement, U = window.ServiceUI;
  const t = key => {
    const value = (window.EventLanguage === 'en' ? window.EventEn : window.EventRu)[key];
    if (value === undefined) throw new Error(`Missing translation: ${key}`);
    return value;
  };
  const text = (tag, key, props = {}) => h(tag, props, t(key));
  const button = (key, onClick, primary = false, disabled = false) => h(U.Button, { onClick, disabled, variant: primary ? 'primary' : 'secondary' }, t(key));
  const icon = name => h(U.Icon, { name, size: 16 });
  const field = (key, value, onChange, extra = {}) => h(U.FormField, { label: t(key), value, onChange, ...extra });
  const select = (key, value, onChange, choices) => h(U.SelectField, { label: t(key), value, onChange, options: choices.map(([v,k]) => [v,t(k)]) });
  const toggle = (key, checked, onClick) => h('div', { className: 'server-enabled' }, text('strong', key), h(U.SwitchButton, { label: t(key), checked, onClick, className: 'ui-switch' }));
  window.EventParts = { h, U, t, text, button, icon, field, select, toggle };
})();
