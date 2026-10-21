(function () {
  const { h } = window.ServiceParts, U = window.ServiceUI, t = window.jt;
  const initial = {
    amo: { name: t('amoName'), address: t('amoAddress'), method: 'oauth', pipeline: t('pipelineSales'), stage: t('stageNew'), owner: '', team: t('support'), connected: false, enabled: false },
    mindbox: { name: t('mindboxName'), address: 'https://api.mindbox.ru', endpoint: '', team: t('support'), connected: false, checked: false, enabled: false },
  };
  function useVendor(service) {
    const journey = window.Journey.useJourney();
    return { ...journey, value: journey.draft.vendors?.[service] || initial[service],
      change: patch => journey.update({ vendors: { ...journey.draft.vendors,
        [service]: { ...(journey.draft.vendors?.[service] || initial[service]), ...patch } } }) };
  }
  function Field({ service, name, label, error, placeholder, help }) {
    const { value, change } = useVendor(service);
    return h('div', null, h(U.FormField, { label: t(label), value: value[name], placeholder: placeholder && t(placeholder),
      error: error && t(error), onChange: next => change({ [name]: next }) }),
      help && h('small', { className: 'si-field-help' }, t(help)));
  }
  function Choice({ service, name, label, options, onChange }) {
    const { value, change } = useVendor(service);
    return h(U.SelectField, { label: t(label), value: value[name], options: options.map(key => [t(key), t(key)]),
      onChange: next => onChange ? onChange(next) : change({ [name]: next }) });
  }
  const validAddress = raw => {
    try { const url = new URL(raw); return url.protocol === 'https:' && !url.username && !url.password && !url.search && !url.hash; }
    catch { return false; }
  };
  window.Vendor = { useVendor, Field, Choice, validAddress };
})();
