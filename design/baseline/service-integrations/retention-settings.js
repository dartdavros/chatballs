(function () {
  const { h, card, actions, note } = window.ServiceParts, W = window.Workbench, U = window.ServiceUI, t = window.jt;
  function Retention() {
    const [saved, save] = window.React.useState({ steps: '7', journal: '30' }), [value, set] = window.React.useState(saved);
    const [confirm, show] = window.React.useState(false), [done, finish] = window.React.useState(false);
    const valid = [value.steps,value.journal].every(raw => /^\d+$/.test(raw) && Number(raw) > 0);
    const apply = () => { save(value); show(false); finish(true); };
    return h('div', { className: 'si-card-body' }, card(t('storageTitle'), h(W.Help, { label: 'retentionHelp' }),
      h('div', { className: 'server-two-fields si-fields' },
        h(W.Field, { label: 'stepRetention', type: 'number', value: value.steps, onChange: steps => { set({ ...value, steps }); finish(false); } }),
        h(W.Field, { label: 'journalRetention', type: 'number', value: value.journal, onChange: journal => { set({ ...value, journal }); finish(false); } })),
      h(W.Help, { label: 'activeRetentionHelp' }), h(W.Help, { label: 'retentionAccess' }), h(W.Help, { label: 'cleanupHelp' }),
      done && note('',t('retentionSaved'),'ok'), h(W.Button, { label: 'saveRetention', primary: true, disabled: !valid,
        onClick: () => Number(value.steps) < Number(saved.steps) || Number(value.journal) < Number(saved.journal) ? show(true) : apply() })),
      confirm && h(window.CanvasDialog, { open: true, onClose: () => show(false), tone: 'warning', icon: 'errorCircle', title: t('shortenRetention'), description: t('shortenHelp'),
        actions: actions(h(W.Button, { label: 'confirmRetention', primary: true, onClick: apply }), h(W.Button, { label: 'cancel', onClick: () => show(false) })) }));
  }
  window.RetentionSettings = Retention;
})();
