(function () {
  const { h, text, card, line, actions, note } = window.ServiceParts, U = window.ServiceUI, t = window.jt;
  const { Action, Link } = window.Journey;
  const { useVendor, Field, validAddress } = window.Vendor;
  function Connect() {
    const { value, change, go } = useVendor('amo');
    const [secret, setSecret] = window.React.useState('');
    const [submitted, setSubmitted] = window.React.useState(false);
    const token = value.method === 'token';
    const submit = () => {
      setSubmitted(true);
      if (!value.name.trim() || !validAddress(value.address) || (token && !secret.trim())) return;
      setSecret('');
      if (token) change({ connected: true });
      go(token ? 'Q04' : 'Q02');
    };
    return h('div', { className: 'si-card-body' },
      card(t('connection'), h(Field, { service: 'amo', name: 'name', label: 'connectionName', error: submitted && !value.name.trim() && 'nameRequired' }),
        h(Field, { service: 'amo', name: 'address', label: 'accountAddress', error: submitted && !validAddress(value.address) && 'addressRequired' }),
        h(U.SelectField, { label: t('accessMethod'), value: value.method, options: [['oauth', t('oauthMethod')], ['token', t('tokenMethod')]],
          onChange: method => { change({ method }); setSecret(''); setSubmitted(false); } })),
      token ? card(t('token'), text('p', t('tokenHelp')),
        h(U.FormField, { label: t('token'), placeholder: t('tokenPlaceholder'), type: 'password', value: secret, onChange: setSecret,
          error: submitted && !secret.trim() ? t('secretRequired') : undefined }), text('small', t('tokenExpiry'), 'si-field-help'))
        : card(t('oauthMethod'), text('p', t('oauthHelp')), text('small', t('oauthRights'), 'si-field-help')),
      note('', t('amoCheck')),
      actions(h(Action, { label: token ? 'checkConnect' : 'oauthContinue', primary: true, onClick: submit }), h(Link, { label: 'cancel', to: 'J01' })));
  }
  function Waiting() {
    return h('div', { className: 'si-card-body' }, note(t('oauthWaiting'), t('oauthWaitingHelp')),
      actions(h(Action, { label: 'oauthReopen', primary: true, to: 'Q02' }), h(Link, { label: 'cancel', to: 'Q01' })));
  }
  function Confirm() {
    const { value, change, go } = useVendor('amo');
    return h('div', { className: 'si-card-body' }, note('', t('oauthConfirmHelp')),
      card(t('account'), line(t('accountAddress'), value.address), line(t('connectionName'), value.name)),
      actions(h(Action, { label: 'confirmConnection', primary: true, onClick: () => { change({ connected: true }); go('Q04'); } }),
        h(Link, { label: 'chooseAnotherAccount', to: 'Q01' })));
  }
  function Unconfigured() {
    const { change, go } = useVendor('amo');
    return h('div', { className: 'si-card-body' }, note(t('oauthNotConfigured'), t('oauthNotConfiguredHelp'), 'warn'),
      actions(h(Action, { label: 'useToken', primary: true, onClick: () => { change({ method: 'token' }); go('Q01'); } })));
  }
  window.AmoConnection = { Connect, Waiting, Confirm, Unconfigured };
})();
