(function () {
  const { h, text, card, table, note } = window.ServiceParts, W = window.Workbench, t = window.jt, L = window.LaunchModel;
  function Schedule({ value: v, set }) {
    return h('div', { className: 'si-form-section' },
      h(W.Select, { label: 'repeatSchedule', value: v.repeat, options: [['weekdays','weekdays'],['daily','daily'],['once','once'],['interval','interval']], onChange: repeat => set({ repeat }) }),
      v.repeat === 'interval' ? h(W.Field, { label: 'pollInterval', type: 'number', value: v.interval, onChange: interval => set({ interval }) })
        : h(W.Field, { label: 'scheduleTime', type: 'time', value: v.time, onChange: time => set({ time }) }),
      v.repeat === 'once' && h(W.Field, { label: 'scheduleDate', type: 'date', value: v.date, onChange: date => set({ date }) }),
      h(W.Select, { label: 'scheduleZone', value: v.zone, options: [['Europe/Moscow','zoneMoscow'],['Europe/Berlin','zoneBerlin']], onChange: zone => set({ zone }) }),
      h(W.Select, { label: 'missedSchedule', value: v.missed, options: [['skip','skipSchedule'],['once','catchupSchedule']], onChange: missed => set({ missed }) }),
      h(W.Select, { label: 'missingHour', value: v.gap, options: [['next','nextHour'],['skip','skipSchedule']], onChange: gap => set({ gap }) }),
      h(W.Select, { label: 'repeatedHour', value: v.fold, options: [['first','firstHour'],['second','secondHour']], onChange: fold => set({ fold }) }),
      text('strong', t('previewSchedule')), table([t('dateColumn'),t('timeColumn'),t('scheduleZone')], L.preview(v)), h(W.Help, { label: 'previewScheduleHelp' }));
  }
  function Launch() {
    const c = window.Custom.use(), R = window.React;
    const [v, update] = R.useState(() => structuredClone(c.plan.launch)), [group, setGroup] = R.useState(c.plan.group), [submitted, submit] = R.useState(false);
    const set = patch => update(old => ({ ...old, ...patch }));
    const errors = L.errors(v), options = {
      manual: () => h(W.Select, { label: 'customGroup', value: group, options: [['support','support'],['sales','sales']], onChange: setGroup }),
      ai: () => h('div', { className: 'si-form-section' },
        h(W.Select, { label: 'agentChoice', value: v.agent, options: [['support','supportAgent']], onChange: agent => set({ agent }) }),
        h(W.Select, { label: 'aiMode', value: v.aiMode, options: [['forbidden','aiForbidden'],['independent','aiIndependent'],['confirm','aiConfirm']], onChange: aiMode => set({ aiMode }) }), h(W.Help, { label: 'permissionHelp' })),
      internal: () => h(W.Select, { label: 'internalEvent', value: v.internalEvent, options: [['transfer','dialogTransferred'],['created','dialogCreated'],['message','dialogMessage']], onChange: internalEvent => set({ internalEvent }) }),
      external: () => h('div', { className: 'si-form-section' },
        h(W.Select, { label: 'eventConnection', value: 'amo', options: [['amo','amoName']], onChange: () => {} }),
        h(W.Select, { label: 'externalEvent', value: v.externalEvent, options: [['deal','dealUpdated']], onChange: externalEvent => set({ externalEvent }) }),
        h(W.Select, { label: 'eventDelivery', value: v.delivery, options: [['webhook','webhookDelivery'],['poll','pollingDelivery']], onChange: delivery => set({ delivery }) }),
        v.delivery === 'poll' && h(W.Field, { label: 'pollInterval', type: 'number', value: v.poll, onChange: poll => set({ poll }) })),
      schedule: () => h(Schedule, { value: v, set }),
      api: () => h('div', { className: 'si-form-section' }, h(W.Select, { label: 'apiAccess', value: v.apiAccess, options: [['corporate','apiPrincipal']], onChange: apiAccess => set({ apiAccess }) }), h(W.Help, { label: 'apiHelp' })),
      nested: () => h(W.Help, { label: 'nestedLaunchHelp' }),
    };
    return h('div', { className: 'si-card-body' }, h(W.Tabs, { active: 'X08' }), h(W.Help, { label: 'launchHelp' }),
      ...['manual','ai','internal','external','schedule','api','nested'].map(key => card('',
        h(W.Toggle, { inline:true, label: `${key}Launch`, help: `${key}LaunchHelp`, checked: v[key], onChange: checked => set({ [key]: checked }) }), v[key] && options[key]())),
      L.automatic(v) && card(t('delegatedAccess'), h(W.Help, { label: 'delegationHelp' }),
        h(W.Select, { label: 'delegationOwner', value: v.owner, options: [['elena','ownerElena']], onChange: owner => set({ owner }) }),
        c.plan.steps.length ? h(window.CustomSteps.Summary, { steps: c.plan.steps }) : h(W.Help, { label: 'noStepsDelegation' }),
        h(W.Toggle, { inline:true,label: 'delegateToggle', checked: v.delegate, onChange: delegate => set({ delegate }) })),
      h(W.Help, { label: 'accessRecheck' }), submitted && errors.map(key => note('',t(key),'error')),
      h(W.Footer, { onApply: () => { submit(true); if (!errors.length) { c.update({ launch: v, group }); c.go('X01'); } } }));
  }
  window.LaunchSettings = { Launch, Schedule };
})();
