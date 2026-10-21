(function () {
  const { h, text, actions } = window.ServiceParts, U = window.ServiceUI, t = window.jt;
  const Button = ({ label, onClick, primary, icon, disabled, danger }) => h(U.Button, { variant: danger ? 'danger-outline' : primary ? 'primary' : 'secondary', onClick, icon, disabled }, t(label));
  const Field = ({ label, ...props }) => h(U.FormField, { label: t(label), ...props });
  const Select = ({ label, options, ...props }) => h(U.SelectField, { label: t(label), options: options.map(([key, value]) => [key, t(value)]), ...props });
  const Help = ({ label }) => text('p', t(label), 'settings-section-note si-note');
  function Toggle({ label, help, checked, onChange, inline }) {
    return h('div', { className: inline ? 'settings-card-head si-inline-toggle' : 'server-enabled' }, h(inline ? 'div' : 'span', null, text('strong', t(label)), help && text('small', t(help))),
      h(U.SwitchButton, { className: 'ui-switch', label: t(label), checked, onClick: () => onChange(!checked) }));
  }
  function Tabs({ active = 'X01' }) {
    const c = window.Custom.use();
    return h(U.UnderlineTabs, { className: 'integrations-tabs si-tabs', value: active,
      items: [['X01','editorTab'],['X08','launchTab'],['X10','schemaTab'],['X11','syncTab']].map(([key,label]) => ({ key, label: t(label) })), onChange: c.go });
  }
  const Footer = ({ onApply, disabled }) => {
    const c = window.Custom.use();
    return actions(h(Button, { label: 'applySettings', primary: true, onClick: onApply, disabled }), h('button', { className: 'link is-muted', type: 'button', onClick: () => c.go('X01') }, t('cancel')));
  };
  window.Workbench = { Button, Field, Select, Help, Toggle, Tabs, Footer };
})();
