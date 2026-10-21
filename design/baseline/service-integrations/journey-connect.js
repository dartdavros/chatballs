(function () {
  const { h, text, card, line, fields, actions, note } = window.ServiceParts;
  const U = window.ServiceUI, t = window.jt;
  const { Action, Link, useJourney } = window.Journey;
  function Catalog({state='ready'}) {
    const [search, setSearch] = window.React.useState('');
    const { go } = useJourney();
    const services = window.JourneyData.services.filter(([key]) => t(key).toLowerCase().includes(search.toLowerCase()));
    return h('div', { className: 'si-card-body' },
      h(U.SearchInput, { placeholder: t('search'), value: search, onChange: setSearch, clearable: true }),
      h(window.CatalogSurface,{state:state==='ready' && !services.length?'search-empty':state,onRetry:()=>go('J01')},
        ...services.map(([key, description]) => line(h(window.ServiceLogo, { service: key }), t(description),
          h(Action, { label: 'connect', onClick: () => go({ bitrix: 'J02', amo: 'Q01', mindbox: 'D01' }[key]) })))),
      note(t('noService'), t('noServiceHelp')));
  }
  function Connect() {
    const { draft, update, go } = useJourney();
    const [secret, setSecret] = window.React.useState('');
    const [submitted, setSubmitted] = window.React.useState(false);
    let valid = false;
    try { const url = new URL(secret); valid = url.protocol === 'https:' && /^\/rest\/\d+\/[^/]+\/?$/.test(url.pathname); } catch {}
    const submit = () => {
      setSubmitted(true);
      if (!draft.connectionName.trim() || !valid) return;
      // Preview-only transition. The entered secret is discarded, never stored or sent.
      setSecret('');
      const extras = [...draft.extraConnections || []];
      if (draft.creatingExtra) extras.push(draft.connectionName);
      update({ connected: true, creatingExtra:false, extraConnections:extras });
      go('J03');
    };
    return h('div', { className: 'si-card-body' },
      card(t('howConnect'), h('ol', { className: 'journey-instructions' },
        ...['hookStep1', 'hookStep2', 'hookStep3'].map(key => h('li', { key }, t(key)))),
        h('a', { className: 'link', href: 'https://apidocs.bitrix24.ru/local-integrations/local-webhooks.html', target: '_blank', rel: 'noopener noreferrer' }, t('instructions'))),
      card(t('connection'),
        h(U.FormField, { label: t('connectionName'), value: draft.connectionName, onChange: value => update({ connectionName: value }),
          error: submitted && !draft.connectionName.trim() ? t('nameRequired') : undefined }),
        h(U.FormField, { label: t('hook'), value: secret, type: 'password', placeholder: t('hookPlaceholder'), onChange: setSecret,
          error: submitted && !valid ? t(secret ? 'hookInvalid' : 'hookRequired') : undefined }),
        text('small', t('hookHint'), 'si-field-help')),
      note('', t('connectionRights')),
      actions(h(Action, { label: 'checkConnect', primary: true, onClick: submit }), h(Link, { label: 'cancel', to: 'J01' })),
      text('small', t('checkHint'), 'si-field-help'));
  }
  function Connected() {
    const { draft } = useJourney();
    const custom = window.Custom.use();
    const current=window.ConnectionDrafts.key(draft),own=custom.saved && custom.origin==='J03' && custom.originConnection===current;
    const archived=custom.archived.filter(item=>item.origin==='J03' && item.originConnection===current);
    return h('div', { className: 'si-card-body' },
      line(t('samplePortal'), t('connected'), h(Link, { label: 'connectionSettings', to: 'J11' })),
      card(t('readyTitle'), text('p', t('readyLead')),
        line(t('leadName'), t('leadAbout'), h(Action, { label: 'configure', primary: true, to: 'J04' })),
        text('small', t('leadRequirement'), 'si-field-help')),
      actions(h(Link, { label: 'ownScenario', onClick: () => custom.open('J03') })),
      own && card(t('scenario'), line(custom.saved.name || t('customTitle'), t(custom.status),
        h(Action, { label: 'editScenario', onClick: () => custom.open('J03') }))),
      ...archived.map(item=>card(t('scenario'),line(item.plan.name,t(item.published?'enabled':'draft'),h(Action,{label:'editScenario',onClick:()=>custom.openArchived(custom.archived.indexOf(item))})))),
      draft.enabled && !own && !archived.length && card(t('scenario'), line(draft.scenarioName, t('enabled'), h(Action, { label: 'editScenario', onClick:()=>custom.fromPreset('bitrix') }))));
  }
  function ConnectionSettings() {
    const { draft, update,beginConnection } = useJourney();
    return card(t('connection'), h(U.FormField, { label: t('connectionName'), value: draft.connectionName,
      onChange: value => update({ connectionName: value }) }), line(t('portal'), t('samplePortal')),
      line(t('retainedSecret'), t('connected'), h(Link, { label: 'replaceAccess', to: 'J02' })),
      actions(h(Action, { label: 'toService', to: 'J03' }), h(Link, { label: 'newConnection', onClick:beginConnection })));
  }
  window.JourneyConnect = { Catalog, Connect, Connected, ConnectionSettings };
})();
