(function () {
  const { h, text, card, line, fields, actions, note } = window.ServiceParts;
  const U = window.ServiceUI, t = window.jt;
  const { Action, Link, CrmFields, Mapping, Step, useJourney } = window.Journey;
  function Editor() {
    const { draft, update, go, save, discard } = useJourney();
    return h('div', { className: 'si-card-body' },
      h(U.FormField, { label: t('editorName'), value: draft.scenarioName, onChange: name => update({ scenarioName: name }) }),
      card(t('when'), line(t('manual'), `${t('team')}: ${draft.team}`, h(Link, { label: 'change', to: 'J04' }))),
      card(t('conditions'), text('p', t('conditionSummary')), text('small', t('existingLink'), 'si-field-help')),
      card(t('steps'), h(Step, { number: '1', title: 'createLead', summary: 'createLeadSummary', editTo: 'J08', service: 'bitrix' }),
        h(Step, { number: '2', title: 'linkLead', summary: 'linkLeadSummary' }),
        draft.tag && h(Step, { number: '3', title: 'addTag', summary: 'tagValue', editTo: 'J09' }),
        h(Action, { label: 'addStep', to: 'J09' })),
      card(t('failure'), text('p', t('failureSummary'))),
      actions(h(Action, { label: 'save', primary: true, disabled: !draft.scenarioName.trim(),
        onClick: () => { save(); go('J06'); } }), h(Link, { label: 'discard', onClick: () => { discard(); go('J06'); } })),
      note('', t('editorHelp')));
  }
  function StepEditor() {
    const journey = useJourney();
    const [local, setLocal] = window.React.useState(journey.draft);
    return h('div', { className: 'si-card-body' },
      h(window.Journey.Context.Provider, { value: { ...journey, draft: local,
        update: patch => setLocal(old => ({ ...old, ...patch })) } }, card(t('crmSettings'), h(CrmFields))), h(Mapping),
      note('', t('stepHint')),
      actions(h(Action, { label: 'applyStep', primary: true,
        onClick: () => { journey.update(local); journey.go('J07'); } }), h(Link, { label: 'cancel', to: 'J07' })));
  }
  function AddStep() {
    const { update, go } = useJourney();
    return h('div', { className: 'si-card-body' },
      card(t('operation'),
        fields(h(U.SelectField, { label: t('sourceService'), value: t('chatballs'), options: [[t('chatballs'), t('chatballs')]], onChange: () => {} }),
          h(U.SelectField, { label: t('operation'), value: t('addTag'), options: [[t('addTag'), t('addTag')]], onChange: () => {} })),
        text('p', t('tagHelp')),
        h(U.SelectField, { label: t('tag'), value: t('tagValue'), options: [[t('tagValue'), t('tagValue')]], onChange: () => {} })),
      actions(h(Action, { label: 'addToScenario', primary: true, onClick: () => { update({ tag: true }); go('J07'); } }),
        h(Link, { label: 'cancel', to: 'J07' })));
  }
  window.JourneyEditor = { Editor, StepEditor, AddStep };
})();
