(function () {
  const h = window.React.createElement, U = window.ServiceUI;
  const t = (key, lang = window.SpeechLanguage || 'ru') => {
    const value = (lang === 'en' ? window.SpeechEn : window.SpeechRu)[key];
    if (value === undefined) throw new Error(`Missing baseline translation: ${lang}/${key}`);
    return value;
  };
  const text = (tag, key, props = {}) => h(tag, props, t(key));
  const action = (key, onClick, primary = false, disabled = false) => h(U.Button,
    { onClick, disabled, variant: primary ? 'primary' : 'secondary' }, t(key));
  const link = (key, onClick) => h('button', { type: 'button', className: 'link is-muted', onClick }, t(key));
  const icon = (name, size = 17) => h(U.Icon, { name, size });
  const spinner = () => h(window.SpeechProduct.LogoSpinner, { size: 20 });
  function Field({ label, value = '', choices, help, disabled, error, type = 'text' }) {
    const [draft, setDraft] = window.React.useState(value);
    const props = { label: t(label), value: draft, onChange: setDraft, disabled };
    return h('div', { className: 'sp-field' }, choices
      ? h(U.SelectField, { ...props, options: choices.map(k => [k, t(k)]) })
      : h(U.FormField, { ...props, type, error: error && t(error) }), help && text('small', help));
  }
  function Toggle({ label, help, checked = false, disabled = false }) {
    const [on, setOn] = window.React.useState(checked);
    return h('div', { className: 'server-enabled' }, h('span', null, text('strong', label), help && text('small', help)),
      h(U.SwitchButton, { className: 'ui-switch', checked: on, disabled, label: t(label), onClick: () => setOn(!on) }));
  }
  const field = (label, value, options = {}) => h(Field, { label, value, ...options });
  const card = (title, ...children) => h('section', { className: 'agent-card sp-card' }, text('h3', title), ...children);
  window.SpeechParts = { h, U, t, text, action, link, icon, spinner, field, card, Toggle };
})();
