(function () {
  const { h, text, card, line, table, actions, note } = window.ServiceParts;
  const t = window.jt;
  const { Action, Link, Choice, CrmFields, Mapping, useJourney } = window.Journey;
  function Setup() {
    const { draft, go } = useJourney();
    const [submitted, setSubmitted] = window.React.useState(false);
    return h('div', { className: 'si-card-body' },
      note(t('resultTitle'), t('resultText')),
      card(t('crmSettings'), h(CrmFields, { error: submitted && !draft.responsible ? 'requiredResponsible' : undefined })),
      h(Mapping),
      card(t('permissions'), h(Choice, { label: 'team', name: 'team', choices: ['support', 'sales'] }), text('small', t('rightsHint'), 'si-field-help')),
      actions(h(Action, { label: 'review', primary: true, onClick: () => { setSubmitted(true); if (draft.responsible) go('J05'); } }),
        h(Link, { label: 'cancel', to: 'J03' })));
  }
  function Review() {
    const { draft, go, save } = useJourney();
    return h('div', { className: 'si-card-body' },
      note('', t('reviewHint')),
      card(t('scenario'), line(t('when'), t('manual')), line(t('permissions'), draft.team),
        line(t('responsible'), draft.responsible || t('chooseResponsible')), line(t('stage'), draft.stage),
        line(t('conditions'), t('conditionSummary')),
        line(t('steps'), `${t('createLead')} → ${t('linkLead')}`), line(t('failure'), t('failureSummary'))),
      actions(h(Action, { label: 'enable', primary: true, disabled: !draft.responsible,
        onClick: () => { save({ enabled: true }); go('J06'); } }), h(Link, { label: 'change', to: 'J04' })));
  }
  function Enabled() {
    const { draft } = useJourney();
    const custom=window.Custom.use();
    return h('div', { className: 'si-card-body' },
      note(t('enabledTitle'), t('enabledText'), 'ok'),
      card(t('scenario'), line(draft.scenarioName, `${draft.team} · ${t('manual')}`),
        line(t('responsible'), draft.responsible || t('memberAnna')),
        line(t('steps'), [t('createLead'), t('linkLead'), ...(draft.tag ? [t('addTag')] : [])].join(' → '))),
      actions(h(Action, { label: 'editScenario', onClick:()=>custom.fromPreset('bitrix'), primary: true }), h(Link, { label: 'toService', to: 'J03' })));
  }
  function Services() {
    const { draft, selectConnection, notify } = useJourney();
    return h('div', { className: 'si-card-body' },
      h(window.ServiceUI.UnderlineTabs, { className: 'integrations-tabs', value: 'services',
        items: ['entries', 'servers', 'services'].map(key => ({ key, label: t(key) })),
        onChange: key => { if (key !== 'services') notify(t('existingSections')); } }),
      table([t('connectionColumn'), t('serviceColumn'), t('state'), ''], [[
        h(Link, { strong:true,label: draft.primaryConnection || draft.connectionName, onClick:()=>selectConnection('bitrix',draft.primaryConnection || draft.connectionName) }), h(window.ServiceLogo, { service: 'bitrix', compact: true }), t('connected'),
        h(Action, { label: 'configure', onClick:()=>selectConnection('bitrix',draft.primaryConnection || draft.connectionName) }),
      ], ...(draft.extraConnections || []).map((name,index) => [h(Link,{strong:true,label:name,onClick:()=>selectConnection(`bitrix-${index}`,name)}),h(window.ServiceLogo,{service:'bitrix',compact:true}),t('connected'),h(Action,{label:'configure',onClick:()=>selectConnection(`bitrix-${index}`,name)})]),
      ...Object.entries(draft.vendors || {}).filter(([, value]) => value.connected).map(([service, value]) => {
        const target = service === 'amo' ? 'Q04' : value.checked ? 'D04' : 'D02';
        return [h(Link, { strong:true,label: value.name, to: target }), h(window.ServiceLogo, { service, compact: true }),
          t(service === 'mindbox' && !value.checked ? 'unchecked' : 'connected'), h(Action, { label: 'configure', to: target })];
      })]), actions(h(Action, { label: 'addService', primary: true, to: 'J01' })));
  }
  window.JourneyScenario = { Setup, Review, Enabled, Services };
})();
