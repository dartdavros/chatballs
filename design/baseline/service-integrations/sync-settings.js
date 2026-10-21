(function () {
  const { h, text, card, line } = window.ServiceParts, W = window.Workbench, t = window.jt;
  const defaults = () => ({ enabled: false, local: 'dialog', remote: 'lead', connection: 'bitrix', identifier: '', direction: 'both', conflict: 'pause', remoteDeleted: 'unlink', localDeleted: 'unlink', mappings: [{ local: 'name', remote: 'name', source: 'service' }] });
  const deletionOptions = [['unlink','keepUnlink'],['pause','pauseDeletion'],['delete','allowDeletion']];
  function Mapping({ value, onChange, onRemove }) {
    const set = patch => onChange({ ...value, ...patch });
    return h('div', { className: 'si-mapping-row' },
      h(W.Select, { label: 'localField', value: value.local, options: [['name','contactNameField'],['email','contactEmailField']], onChange: local => set({ local }) }),
      h(W.Select, { label: 'remoteField', value: value.remote, options: [['name','remoteNameField'],['email','remoteEmailField']], onChange: remote => set({ remote }) }),
      h(W.Select, { label: 'mainSource', value: value.source, options: [['service','serviceColumn'],['chatballs','chatballs']], onChange: source => set({ source }) }),
      h(window.ServiceUI.Button, { variant: 'secondary', icon: 'trash', onClick: onRemove, 'aria-label': t('removeParameter') }, t('removeParameter')));
  }
  function Sync() {
    const c = window.Custom.use(), [v, update] = window.React.useState(() => structuredClone(c.plan.sync)), set = patch => update(old => ({ ...old, ...patch }));
    return h('div', { className: 'si-card-body' }, h(W.Tabs, { active: 'X11' }),
      card(t('relationships'), h(W.Help, { label: 'relationshipsHelp' }),
        h(W.Select, { label: 'localEntity', value: v.local, options: [['dialog','entityDialog'],['contact','entityContact']], onChange: local => set({ local }) }),
        h(W.Select, { label: 'connectionSelect', value: v.connection, options: [['bitrix','defaultName'],['amo','amoName']], onChange: connection => set({ connection, remote: connection === 'amo' ? 'deal' : 'lead' }) }),
        h(W.Select, { label: 'remoteEntity', value: v.remote, options: v.connection === 'amo' ? [['deal','entityDeal']] : [['lead','entityLead']], onChange: remote => set({ remote }) }),
        h(W.Field, { label: 'externalIdentifier', value: v.identifier, onChange: identifier => set({ identifier }) }), h(W.Help, { label: 'noBindings' })),
      h(W.Toggle, { label: 'syncEnabled', help: 'syncHelp', checked: v.enabled, onChange: enabled => set({ enabled }) }),
      v.enabled && card(t('mappings'),
        ...v.mappings.map((mapping,index) => h(Mapping, { key: index, value: mapping,
          onChange: value => set({ mappings: v.mappings.map((old,i) => i === index ? value : old) }), onRemove: () => set({ mappings: v.mappings.filter((_,i) => i !== index) }) })),
        h(W.Button, { label: 'addMapping', icon: 'plus', onClick: () => set({ mappings: [...v.mappings,{ local: 'name', remote: 'name', source: 'service' }] }) }),
        h(W.Select, { label: 'syncDirection', value: v.direction, options: [['out','toService'],['in','fromService'],['both','bothDirections']], onChange: direction => set({ direction }) }),
        h(W.Select, { label: 'conflictPolicy', value: v.conflict, options: [['pause','pauseConflict'],['source','preferSource']], onChange: conflict => set({ conflict }) }),
        h(W.Select, { label: 'serviceDeletion', value: v.remoteDeleted, options: deletionOptions, onChange: remoteDeleted => set({ remoteDeleted }) }),
        h(W.Select, { label: 'localDeletion', value: v.localDeleted, options: deletionOptions, onChange: localDeleted => set({ localDeleted }) }),
        h(W.Help, { label: 'syncLoopHelp' })),
      h(W.Footer, { disabled: v.enabled && (!v.identifier.trim() || !v.mappings.length), onApply: () => { c.update({ sync: v }); c.go('X01'); } }));
  }
  function Conflict() {
    const [value, set] = window.React.useState('remote'), [resolved, resolve] = window.React.useState(false), c = window.Custom.use();
    return h('div', { className: 'si-card-body' }, card(t('conflictTitle'), h(W.Help, { label: 'conflictHelp' }),
      line(t('chatballs'), t('localConflict')), line(t('serviceColumn'),t('remoteConflict')),
      h(W.Select, { label: 'chooseConflict', value, options: [['remote','remoteConflict'],['local','localConflict']], onChange: set }),
      resolved ? h(W.Help, { label: 'conflictResolved' }) : h(W.Button, { label: 'applyConflict', primary: true, onClick: () => resolve(true) })),
      h(W.Button, { label: 'pauseConflictAction', onClick: () => c.go('X11') }));
  }
  window.SyncSettings = { defaults, Sync, Conflict };
})();
