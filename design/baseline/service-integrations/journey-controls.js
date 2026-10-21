// Reusable compositions for the proposed path, using actual shared controls.
(function () {
  const { h, text, card, fields, actions } = window.ServiceParts;
  const U = window.ServiceUI, t = window.jt;
  const Context = window.React.createContext(null);
  const useJourney = () => window.React.useContext(Context);
  function Action({ label, to, primary, onClick, disabled }) {
    const { go } = useJourney();
    return h(U.Button, { variant: primary ? 'primary' : 'secondary', disabled,
      onClick: onClick || (() => go(to)) }, t(label));
  }
  function Link({ label, to, onClick, strong = false }) {
    const { go } = useJourney();
    if (['ownScenario','change','changeStep','replaceAccess','newConnection'].includes(label))
      return h(U.Button, { variant: 'secondary', onClick: onClick || (() => go(to)) }, t(label));
    return h('button', { type: 'button', className: `link${strong ? ' is-strong' : ['cancel','discard','back','toService','backToConnection'].includes(label) ? ' is-muted' : ''}`, onClick: onClick || (() => go(to)) }, t(label));
  }
  function Choice({ label, name, choices, error }) {
    const { draft, update } = useJourney();
    return h('div', null, h(U.SelectField, { label: t(label), value: draft[name],
      options: choices.map(key => [t(key), t(key)]), invalid: !!error, onChange: value => update({ [name]: value }) }),
      error && text('small', t(error), 'form-field-error'));
  }
  function CrmFields({ error }) {
    return h(window.React.Fragment, null,
      fields(h(Choice, { label: 'responsible', name: 'responsible', choices: ['memberAnna', 'memberDmitry'], error }),
        h(Choice, { label: 'stage', name: 'stage', choices: ['stageValue'] }),
        h(Choice, { label: 'source', name: 'source', choices: ['sourceValue'] })),
      text('small', t('directoryHint'), 'si-field-help'));
  }
  function Mapping() {
    const { table } = window.ServiceParts;
    return card(t('dataTitle'), table([t('crmField'), t('fromChatballs')], [
      [t('leadTitle'), t('leadTitleValue')], [t('name'), t('contactName')],
      [t('phone'), t('contactPhone')], [t('email'), t('contactEmail')],
    ]), text('small', t('optionalContact'), 'si-field-help'));
  }
  function Step({ number, title, summary, editTo, service }) {
    return h('section', { className: 'si-block' }, h('header', null,
      text('span', number, 'si-step-number'), h('div', null,
        h('div', { className: 'journey-step-title' }, text('h3', t(title)), service && h(window.ServiceLogo, { service, compact: true })), text('p', t(summary))),
      editTo && h(Link, { label: 'changeStep', to: editTo })));
  }
  window.Journey = { Context, useJourney, Action, Link, Choice, CrmFields, Mapping, Step };
})();
