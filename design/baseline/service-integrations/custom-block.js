(function () {
  const { h, text, card, actions, note } = window.ServiceParts, U = window.ServiceUI, M = window.CustomModel, t = window.jt;
  const { button, link } = window.CustomEditor;
  function BlockForm() {
    const c = window.Custom.use();
    const [step, setStep] = window.React.useState(() => {
      const existing = c.selection.id && M.visit(c.plan.steps, c.selection.id);
      return structuredClone(existing && existing.kind !== 'action' ? existing : M.makeStep(c.selection.kind === 'action' ? 'branch' : c.selection.kind));
    });
    const [submitted, setSubmitted] = window.React.useState(false);
    const p = step.params, set = patch => setStep(old => ({ ...old, params: { ...old.params, ...patch } }));
    const select = (label, name, choices, fallback) => h(U.SelectField, { label: t(label), value: p[name] || fallback || choices[0][0],
      options: choices.map(([key, labelKey]) => [key,t(labelKey)]), onChange: value => set({ [name]: value }) });
    const field = (label, name, type = 'text') => h(U.FormField, { label: t(label), value: p[name] || '', type, onChange: value => set({ [name]: value }) });
    const content = {
      branch: () => [select('checkField','condition',[['contact','contactPresent'],['tag','conditionTag']]), p.condition === 'tag' && field('conditionValue','tag')],
      each: () => [select('listSource','list',[['files','inputFiles']]), select('eachOrder','order',[['serial','sequential'],['parallel','independent']]),
        select('itemFailure','failure',[['stop','stopRun'],['continue','continueItems']]),note('',t('loopResultsHelp'))],
      parallel: () => [select('parallelFailure','failure',[['all','waitAll']]), note('', t('parallelHelp'))],
      nested: () => [select('nestedChoice','scenario',[['notify','nestedNotify']]), select('nestedEmployee','employee',[['owner','dialogOwner']]),note('',t('nestedResultHelp')), note('',t('nestedHelp'))],
      delay: () => [select('delayMode','mode',[['duration','durationMode'],['date','dateMode']]), p.mode === 'date' ? field('untilTime','date','datetime-local') : field('minutes','minutes','number'),
        select('timezone','timezone',[['organization','orgTimezone']])],
      event: () => [select('eventKind','event',[['reply','customerReply']]), select('eventMatch','match',[['dialog','currentDialog']]), field('timeoutMinutes','minutes','number'), select('timeoutAction','timeout',[['stop','timeoutStop']])],
      approval: () => [select('approver','approver',[['owner','dialogOwner']]), field('confirmationText','message'), field('timeoutMinutes','minutes','number'),
        select('timeoutAction','timeout',[['stop','timeoutStop']]),select('rejectedAction','rejected',[['stop','timeoutStop']]), note('',t('approvalHelp'))],
      try: () => [select('errorKinds','errors',[['known','knownErrors']]), select('afterError','after',[['error','finishError']]), note('',t('unknownOutcomeHelp'))],
    };
    const invalid = M.invalidBlock(step);
    return h('div', { className: 'si-card-body' }, card(t(M.kinds.find(k=>k[0]===step.kind)[1]), ...content[step.kind](),
      submitted && invalid && text('small', t('customParameterError'), 'form-field-error')),
      actions(button('applyStep', () => { setSubmitted(true); if (!invalid) c.apply(step); }, true), link('cancel', () => c.go('X01'))));
  }
  function Conditions() {
    const c = window.Custom.use();
    const [condition, setCondition] = window.React.useState(c.plan.condition), [tag, setTag] = window.React.useState(c.plan.tag);
    return card(t('conditions'), h(U.SelectField, { label: t('checkField'), value: condition,
      options: [['none',t('noCondition')],['contact',t('contactPresent')],['tag',t('conditionTag')]], onChange: setCondition }),
      condition === 'tag' && h(U.FormField, { label: t('conditionValue'), value: tag, onChange: setTag }),
      actions(button('applyStep', () => { c.update({ condition, tag }); c.go('X01'); }, true, condition === 'tag' && !tag.trim()), link('cancel', () => c.go('X01'))));
  }
  function Launch() {
    const c = window.Custom.use();
    const [group, setGroup] = window.React.useState(c.plan.group);
    return card(t('customLaunch'), text('p',t('customManual')), h(U.SelectField, { label: t('customGroup'), value: group,
      options: ['support','sales'].map(k=>[k,t(k)]), onChange: setGroup }), note('',t('customLaunchHelp')),
      actions(button('applyStep', () => { c.update({ group }); c.go('X01'); }, true), link('cancel', () => c.go('X01'))));
  }
  window.CustomForms = { BlockForm, Conditions, Launch };
})();
