(function () {
  const { h, text, card, line, actions, note } = window.ServiceParts, U = window.ServiceUI, t = window.jt;
  const { Action, Link } = window.Journey;
  const { useVendor, Field, validAddress } = window.Vendor;
  function Connect() {
    const { value, change, go } = useVendor('mindbox');
    const [secret, setSecret] = window.React.useState('');
    const [submitted, setSubmitted] = window.React.useState(false);
    const submit = () => {
      setSubmitted(true);
      if (!value.name.trim() || !validAddress(value.address) || !value.endpoint.trim() || !secret.trim()) return;
      setSecret(''); change({ connected: true, checked: false, enabled: false }); go('D02');
    };
    return h('div', { className: 'si-card-body' },
      card(t('connection'), h(Field, { service: 'mindbox', name: 'name', label: 'connectionName', error: submitted && !value.name.trim() && 'nameRequired' }),
        h(Field, { service: 'mindbox', name: 'address', label: 'apiAddress', help: 'apiAddressHelp', error: submitted && !validAddress(value.address) && 'addressRequired' }),
        h(Field, { service: 'mindbox', name: 'endpoint', label: 'endpoint', placeholder: 'endpointPlaceholder', error: submitted && !value.endpoint.trim() && 'endpointRequired' }),
        h(U.FormField, { label: t('secretKey'), placeholder: t('secretPlaceholder'), type: 'password', value: secret, onChange: setSecret,
          error: submitted && !secret.trim() ? t('secretRequired') : undefined }), text('small', t('mindboxCredentials'), 'si-field-help')),
      note('', t('mindboxSafeHelp')),
      actions(h(Action, { label: 'saveConnection', primary: true, onClick: submit }), h(Link, { label: 'cancel', to: 'J01' })));
  }
  function Saved() {
    const { value } = useVendor('mindbox');
    return h('div', { className: 'si-card-body' }, note(t('savedUnchecked'), t('mindboxSafeHelp'), 'warn'),
      card(t('connection'), line(t('connectionName'), value.name), line(t('endpoint'), value.endpoint || 'Chatballs'), line(t('state'), t('unchecked'))),
      actions(h(Action, { label: 'checkAccess', primary: true, to: 'D03' }), h(Link, { label: 'change', to: 'D01' })));
  }
  function Check() {
    const { change, go } = useVendor('mindbox');
    const [customer, setCustomer] = window.React.useState('');
    const [submitted, setSubmitted] = window.React.useState(false);
    return h('div', { className: 'si-card-body' },
      card(t('readOperation'), h(U.SelectField, { label: t('readOperation'), value: 'read', options: [['read', t('readCustomer')]], onChange: () => {} }),
        text('small', t('mindboxOperationHelp'), 'si-field-help'),
        h(U.FormField, { label: t('existingCustomer'), value: customer, onChange: setCustomer,
          error: submitted && !customer.trim() ? t('customerRequired') : undefined }), text('small', t('existingCustomerHelp'), 'si-field-help')),
      actions(h(Action, { label: 'checkRead', primary: true, onClick: () => {
        setSubmitted(true); if (customer.trim()) { setCustomer(''); change({ checked: true, connected: true }); go('D04'); }
      } }), h(Link, { label: 'cancel', to: 'D02' })));
  }
  window.MindboxConnection = { Connect, Saved, Check };
})();
