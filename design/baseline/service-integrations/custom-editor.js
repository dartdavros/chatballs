(function () {
  const { h, text, card, line, actions, note } = window.ServiceParts, U = window.ServiceUI, M = window.CustomModel, t = window.jt;
  const button = (label, onClick, primary = false, disabled = false) => h(U.Button, { variant: primary ? 'primary' : 'secondary', onClick, disabled }, t(label));
  const link = (label, onClick, disabled = false) => h('button', { className: 'link is-muted', type: 'button', onClick, disabled }, t(label));
  const { Steps, title, summary } = window.CustomSteps;
  function Editor() {
    const c = window.Custom.use();
    return h('div', { className: 'si-card-body' },
      h(window.Workbench.Tabs),
      h(U.FormField, { label: t('customName'), placeholder: t('customNamePlaceholder'), value: c.plan.name, wide: true, onChange: name => c.update({ name }) }),
      c.published && note('', t('customLiveDisabled')),
      card('', line(t('when'), Object.entries(c.plan.launch).filter(([key,value]) => value === true && ['manual','ai','internal','external','schedule','api','nested'].includes(key)).map(([key])=>t(`${key}Launch`)).join(' · '), button('change', () => c.go('X08'))),
        line(t('conditions'), c.plan.conditions?.rules.length > 1 || c.plan.condition === 'group' ? t('groupedConditions') : c.plan.condition === 'tag' ? `${t('conditionTag')}: ${c.plan.tag}` : t(c.plan.condition === 'none' ? 'customConditionEmpty' : 'contactPresent'), button('customAddCondition', () => c.go('X04')))),
      card(t('steps'), text('p', t(c.plan.steps.length ? 'customStepsHelp' : 'customEmptyHelp')), h(Steps, { steps: c.plan.steps })),
      actions(button('checkScenario', () => c.go('X06'), true), button('saveDraft', c.save), link('cancel', c.leave)));
  }
  function Palette() {
    const c = window.Custom.use();
    const [expanded, setExpanded] = window.React.useState(false);
    return h('div', { className: 'si-card-body' },
      card(t('customAction'), text('p', t('customActionHelp')), button('chooseAction', () => c.choose('action'), true)),
      h(U.Button, { variant: 'secondary', className: 'si-palette-toggle', icon: 'chevron', 'aria-expanded': expanded,
        onClick: () => setExpanded(!expanded) }, t(expanded ? 'hideAdvanced' : 'showAdvanced')),
      expanded && card(t('advancedSteps'), ...M.kinds.slice(1).map(([kind, name, help]) => line(t(name), t(help), button('configure', () => c.choose(kind))))),
      actions(link('cancel', () => c.go('X01'))));
  }
  function Review() {
    const c = window.Custom.use(), errors = M.errors(c.plan);
    return h('div', { className: 'si-card-body' }, note(t(errors.length ? 'customInvalid' : 'customValid'), t('customValidHelp'), errors.length ? 'warn' : 'ok'),
      errors.length ? card(t('customInvalid'), ...errors.map(key => text('p', t(key)))) : card(c.plan.name,
        line(t('when'), Object.entries(c.plan.launch).filter(([key,value]) => value === true && ['manual','ai','internal','external','schedule','api','nested'].includes(key)).map(([key])=>t(`${key}Launch`)).join(' · ')), line(t('customGroup'), t(c.plan.group)),
        h(window.ConditionEditor.Summary, { value:c.plan.conditions }),
        h(window.CustomSteps.Summary, { steps: c.plan.steps })),
      !errors.length && c.plan.inputs.length>0 && card(t('inputSchema'),...c.plan.inputs.map(input=>line(input.name,t(window.SchemaEditor.label(input.type))))),
      !errors.length && c.plan.outputs.length>0 && card(t('outputSchema'),...c.plan.outputs.map(output=>line(output.name,window.ValueSummary(output.binding,c.plan.steps,c.plan.inputs)))),
      note('', t('unknownOutcomeHelp')),
      actions(button('enable', c.enable, true, !!errors.length), button('customBack', () => c.go('X01'))));
  }
  function Saved() {
    const c = window.Custom.use(), active = c.published && JSON.stringify(c.published) === JSON.stringify(c.saved);
    return h('div', { className: 'si-card-body' }, note(t(active ? 'customEnabled' : 'savedDraft'), t(active ? 'enabledText' : 'savedDraftHelp'), active ? 'ok' : 'info'),
      card(c.saved?.name || t('customTitle'), line(t('steps'), (c.saved?.steps || []).map(title).join(' → '))),
      actions(button('customBack', () => c.go('X01'), true), button('checkScenario', () => c.go('X06')), link('backToConnection', c.leave)));
  }
  function Unsaved() {
    const c = window.Custom.use();
    return h(window.React.Fragment,null,h(Editor),h(window.CanvasDialog,{open:true,onClose:()=>c.go('X01'),tone:'warning',icon:'errorCircle',title:t('customUnsaved'),description:t('customUnsavedHelp'),
      actions:actions(button('saveAndLeave', c.saveLeave, true), button('leaveWithoutSave', c.discardLeave), link('keepEditing', () => c.go('X01')))}));
  }
  window.CustomEditor = { Editor, Palette, Review, Saved, Unsaved, Steps, button, link, title };
})();
