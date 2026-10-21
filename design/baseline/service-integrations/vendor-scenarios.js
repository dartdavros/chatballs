(function () {
  const { h, text, card, line, fields, actions, note } = window.ServiceParts, t = window.jt;
  const { Action, Link } = window.Journey, { useVendor, Choice } = window.Vendor;
  const config = { amo: { prefix: 'Q', preset: 'amoPreset', help: 'amoPresetHelp', conditions: 'amoConditions', steps: 'amoSteps' },
    mindbox: { prefix: 'D', preset: 'mindboxPreset', help: 'mindboxPresetHelp', conditions: 'mindboxConditions', steps: 'mindboxSteps' } };
  function Profile({ service }) {
    const { value, notify } = useVendor(service), c = config[service];
    const custom = window.Custom.use();
    const own=custom.saved && custom.origin===`${c.prefix}04` && custom.originConnection===service;
    const archived=custom.archived.filter(item=>item.originConnection===service);
    return h('div', { className: 'si-card-body' },
      line(value.address, t(service === 'mindbox' ? 'checked' : 'connected'), h(Link, { label: 'connectionSettings', to: `${c.prefix}01` })),
      service === 'mindbox' && line(t('endpoint'), value.endpoint || 'Chatballs'),
      card(t('readyTitle'), text('p', t('readyLead')),
        line(t(c.preset), t(c.help), h(Action, { label: 'configure', primary: true, to: `${c.prefix}05` }))),
      value.enabled && !own && !archived.length && card(t('scenario'), line(t(c.preset), t('enabled'), h(Action, { label: 'editScenario', onClick:()=>custom.fromPreset(service) }))),
      own && card(t('scenario'), line(custom.saved.name || t('customTitle'), t(custom.status),
        h(Action, { label: 'editScenario', onClick: () => custom.open(`${c.prefix}04`) }))),
      ...archived.map(item=>card(t('scenario'),line(item.plan.name,t(item.published?'enabled':'draft'),h(Action,{label:'editScenario',onClick:()=>custom.openArchived(custom.archived.indexOf(item))})))),
      actions(h(Link, { label: 'ownScenario', onClick: () => custom.open(`${c.prefix}04`) })));
  }
  function Setup({ service }) {
    const parent = useVendor(service), c = config[service];
    const [value, setValue] = window.React.useState(parent.value);
    const change = patch => setValue(old => ({ ...old, ...patch }));
    const [submitted, setSubmitted] = window.React.useState(false);
    const valid = service !== 'amo' || !!value.owner;
    return h(window.Journey.Context.Provider, { value: { ...parent,
      draft: { ...parent.draft, vendors: { ...parent.draft.vendors, [service]: value } },
      update: patch => setValue(patch.vendors[service]) } }, h('div', { className: 'si-card-body' }, note('', t(c.help)),
      service === 'amo' ? card(t('amo'), fields(
        h(Choice, { service, name: 'pipeline', label: 'pipeline', options: ['pipelineSales', 'pipelinePartners'],
          onChange: pipeline => change({ pipeline, stage: t(pipeline === t('pipelineSales') ? 'stageNew' : 'stagePartner') }) }),
        h(Choice, { service, name: 'stage', label: 'dealStage', options: [value.pipeline === t('pipelineSales') ? 'stageNew' : 'stagePartner'] }),
        h(Choice, { service, name: 'owner', label: 'dealOwner', options: ['memberAnna', 'memberDmitry'] })),
        submitted && !valid && text('small', t('requiredSettings'), 'form-field-error'), text('small', t('amoDirectory'), 'si-field-help'))
        : card(t('mindbox'), line(t('readOperation'), t('readCustomer')), line(t('customerSource'), t('linkedCustomer')),
          line(t('resultFields'), t('customerResult')), text('small', t('mindboxResultHelp'), 'si-field-help')),
      card(t('dataTitle'), text('p', t(service === 'amo' ? 'amoData' : 'mindboxData'))),
      card(t('permissions'), h(Choice, { service, name: 'team', label: 'team', options: ['support', 'sales'] }), text('small', t('rightsHint'), 'si-field-help')),
      actions(h(Action, { label: 'review', primary: true, onClick: () => { setSubmitted(true); if (valid) { parent.change(value); parent.go(`${c.prefix}06`); } } }),
        h(Link, { label: 'cancel', to: `${c.prefix}04` }))));
  }
  function Review({ service, enabled = false }) {
    const { value: draft, change, go } = useVendor(service), c = config[service];
    const custom=window.Custom.use();
    const value = enabled && draft.savedPlan ? { ...draft, ...draft.savedPlan } : draft;
    return h('div', { className: 'si-card-body' },
      note(enabled ? t('enabledTitle') : '', t(enabled ? 'enabledText' : 'vendorReviewHint'), enabled ? 'ok' : 'info'),
      card(t(c.preset), line(t('when'), t('manual')), line(t('permissions'), value.team),
        ...(service === 'amo' ? [line(t('pipeline'), `${value.pipeline} · ${value.stage}`), line(t('dealOwner'), value.owner || t('chooseResponsible'))] : []),
        line(t('conditions'), t(c.conditions)), line(t('steps'), t(c.steps)),
        line(t('failure'), t(service === 'amo' ? 'amoFailure' : 'readonlyFailure'))),
      note('', t('copiedPreset')),
      actions(enabled ? h(Action, { label: 'editScenario', primary: true, onClick:()=>custom.fromPreset(service) })
        : h(Action, { label: 'enable', primary: true, disabled: service === 'amo' ? !value.owner : !value.checked,
          onClick: () => { change({ enabled: true, savedPlan: { owner: value.owner, team: value.team, pipeline: value.pipeline, stage: value.stage } }); go(`${c.prefix}10`); } }),
        h(Link, { label: 'backToConnection', to: `${c.prefix}04` })));
  }
  window.VendorScenarios = { Profile, Setup, Review };
})();
