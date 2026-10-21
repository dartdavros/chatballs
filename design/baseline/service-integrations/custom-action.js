(function () {
  const { h, text, card, fields, actions, note } = window.ServiceParts, U = window.ServiceUI, M = window.CustomModel, t = window.jt;
  const { button, link } = window.CustomEditor;
  function ActionForm() {
    const c = window.Custom.use(), selection = c.selection;
    const journey=window.Journey.useJourney();
    const [step, setStep] = window.React.useState(() => {
      const existing = selection.id && M.visit(c.plan.steps, selection.id);
      return structuredClone(existing?.kind === 'action' ? existing : M.makeStep('action'));
    });
    const [submitted, setSubmitted] = window.React.useState(false);
    const [expanded, expand] = window.React.useState(false);
    const [group,setGroup] = window.React.useState(()=>window.PlatformActions.groupOf(step.operation));
    const update = patch => setStep(old => ({ ...old, ...patch }));
    const op = M.operations[step.service].find(o => o[0] === step.operation), type = op[3];
    const operations = M.operations[step.service].filter(o=>step.service !== 'chatballs' || window.PlatformActions.groupOf(o[0]) === group);
    const list = M.siblings(c.plan.steps, selection.parent, selection.slot);
    const index = selection.id ? list.findIndex(s => s.id === selection.id) : list.length;
    const priorSteps=list.slice(0,index), previous = priorSteps.filter(s => s.kind === 'action' && ['lead','deal','customer'].includes(s.operation));
    const extraValid=Object.entries(step.bindings || {}).every(([key,binding])=>window.BindingValid(binding,window.ActionBindingTypes[key],priorSteps,c.plan.inputs)) && (type!=='file' || window.BindingValid(step,'file',priorSteps,c.plan.inputs));
    const options = type === 'record' ? [['constant', t('valueConstant')], ['step', t('valueStep')]]
      : [['constant', t('valueConstant')], ['context', t('valueContext')], ['input', t('valueInput')], ['event', t('valueEvent')], ['directory', t('valueDirectory')],
        ...selection.parent && M.visit(c.plan.steps, selection.parent)?.kind === 'each' ? [['iteration',t('valueIteration')]] : []];
    const select = (label, value, entries, onChange) => h(U.SelectField, { label: t(label), value, options: entries, onChange });
    const connections=[['bitrix',journey.draft.primaryConnection || journey.draft.connectionName],...(journey.draft.extraConnections || []).map((name,index)=>[`bitrix-${index}`,name]),
      ['amo',journey.draft.vendors?.amo?.name || t('amoName')],['mindbox',journey.draft.vendors?.mindbox?.name || t('mindboxName')],['chatballs',t('chatballs')]];
    let control;
    if (type === 'linked') control = note('', t('mindboxData'));
    else if(type==='file')control=h(window.BindingEditor,{value:step,expected:'file',previous:priorSteps,inLoop:!!selection.parent && M.visit(c.plan.steps,selection.parent)?.kind==='each',onChange:update});
    else if (type === 'employee') control = select(op[2], step.value, ['memberAnna','memberDmitry'].map(k => [t(k),t(k)]), value => update({ value }));
    else if (step.source === 'step') control = h('div', null,
      select('resultStep', step.value, previous.map(s => [s.id, window.CustomEditor.title(s)]), value => update({ value })),
      text('small', t('recordId'), 'si-field-help'));
    else if (step.source === 'context') control = select(op[2], step.value, ['contextTitle','contextId','contextContact'].map(k => [t(k),t(k)]), value => update({ value }));
    else if (step.source === 'event' || step.source === 'directory' || step.source === 'iteration') control = select(op[2], step.value,
      ({ event: ['eventTitle','eventTime'], directory: ['stageValue','memberAnna','memberDmitry'], iteration: ['iterationFile','iterationName'] }[step.source]).map(k => [t(k),t(k)]), value => update({ value }));
    else control = h(U.FormField, { label: t(step.source === 'input' ? 'inputLabel' : op[2]), value: step.value, onChange: value => update({ value }) });
    const sourceControl=!['linked','employee','file'].includes(type) && h('div',{className:'si-form-section'},
      select('paramSource',step.source,options,source=>update({source,value:''})),
      text('small',t({constant:'dataHelpConstant',context:'dataHelpContext',input:'dataHelpInput',step:'dataHelpStep',event:'dataHelpEvent',directory:'dataHelpDirectory',iteration:'dataHelpIteration'}[step.source]),'si-field-help'));
    return h('div', { className: 'si-card-body si-form-section' },
      card(h('span',{className:'journey-step-title'},text('span',t('actionSection')),step.service!=='chatballs' && h(window.ServiceLogo,{service:step.service,compact:true})),
        fields(select('connectionSelect', step.connection || step.service, connections, connection => {const service=connection.split('-')[0];setGroup('tags');update({ connection,service, operation: M.operations[service][0][0], source: 'constant', value: '',params:{} });}),
        step.service==='chatballs' && select('actionGroup',group,window.PlatformActions.rows.map(([key,label])=>[key,t(label)]),value=>{setGroup(value);const next=M.operations.chatballs.find(o=>window.PlatformActions.groupOf(o[0])===value);update({operation:next[0],source:'constant',value:''});}),
        select('actionSelect', step.operation, operations.map(o => [o[0],t(o[1])]), operation => update({ operation, source: 'constant', value: '' })))),
      ['lead','deal'].includes(step.operation) && card(t('crmSettings'),fields(
        select(step.service==='bitrix'?'responsible':'dealOwner',step.params.owner || '',['memberAnna','memberDmitry'].map(key=>[t(key),t(key)]),owner=>update({params:{...step.params,owner}})),
        step.service==='amo' && select('pipeline',step.params.pipeline || t('pipelineSales'),['pipelineSales','pipelinePartners'].map(key=>[t(key),t(key)]),pipeline=>update({params:{...step.params,pipeline,stage:t(pipeline===t('pipelinePartners')?'stagePartner':'stageNew')}})),
        select(step.service==='bitrix'?'stage':'dealStage',step.params.stage || '',(step.service==='bitrix'?['stageValue']:[step.params.pipeline===t('pipelinePartners')?'stagePartner':'stageNew']).map(key=>[t(key),t(key)]),stage=>update({params:{...step.params,stage}})))),
      card(t('dataSection'), ['linked','file'].includes(type)?control:fields(sourceControl,control),
        submitted && type !== 'linked' && !step.value.trim() && text('small', t('customParameterError'), 'form-field-error')),
      ['lead','deal'].includes(step.operation) && h(window.ServiceUI.Button, { variant: 'secondary', 'aria-expanded': expanded, onClick: () => expand(!expanded) }, t(expanded ? 'hideParameters' : 'moreParameters')),
      expanded && card(t('moreParameters'), text('p',t('bindingHelp')),
        step.service==='bitrix' && select('source',step.params.source || t('sourceValue'),[[t('sourceValue'),t('sourceValue')]],source=>update({params:{...step.params,source}})),
        ...Object.entries(window.ActionBindingTypes).map(([key, expected]) => h('section', { className: 'si-form-section', key },
          text('h3', t(key)), h(window.BindingEditor, { label: key, value: step.bindings?.[key] || { source: 'constant', value: '' }, expected, previous:priorSteps,
            inLoop: !!selection.parent && M.visit(c.plan.steps, selection.parent)?.kind === 'each', onChange: binding => update({ bindings: { ...step.bindings, [key]: binding } }) })))),
      step.service==='chatballs' && note('',t('actionRightsHelp')),
      actions(button('applyStep', () => { setSubmitted(true); if (extraValid && (type === 'linked' || step.value.trim())) c.apply(step); }, true), link('cancel', () => c.go('X01'))));
  }
  window.CustomAction = ActionForm;
})();
