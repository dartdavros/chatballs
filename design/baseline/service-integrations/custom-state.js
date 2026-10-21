(function () {
  const R = window.React, { h } = window.ServiceParts, M = window.CustomModel;
  const Context = R.createContext(null);
  function Provider({ children }) {
    const { go,draft } = window.Journey.useJourney();
    const [plan, setPlan] = R.useState(M.blank), [saved, setSaved] = R.useState(null), [published, setPublished] = R.useState(null);
    const [selection, setSelection] = R.useState({ parent: null, slot: null, id: null, kind: 'branch' });
    const [origin, setOrigin] = R.useState('J03');
    const [originConnection,setOriginConnection]=R.useState('bitrix');
    const [archived,setArchived] = R.useState([]);
    const dirty = JSON.stringify(plan) !== JSON.stringify(saved || M.blank());
    const editList = fn => setPlan(old => { const next = structuredClone(old); fn(next.steps); return next; });
    const status = published && JSON.stringify(published) === JSON.stringify(saved) ? 'enabled' : 'draft';
    const scope=from=>from==='J03'?window.ConnectionDrafts.key(draft):from==='Q04'?'amo':'mindbox';
    const archiveCurrent=()=>{if(saved)setArchived(old=>old.some(item=>item.originConnection===originConnection && JSON.stringify(item.plan)===JSON.stringify(saved))?old:[...old,{plan:structuredClone(saved),published:structuredClone(published),origin,originConnection}]);};
    const value = { plan, saved, published, selection, origin,originConnection, dirty, status, archived, go,
      update: patch => setPlan(old => ({ ...old, ...patch })),
      open: from => { const connection=scope(from);if(connection!==originConnection || from!==origin){archiveCurrent();setPlan(M.blank());setSaved(null);setPublished(null);}setOriginConnection(connection);setOrigin(from); go('X01'); },
      fromPreset: service => {archiveCurrent();const next=window.PresetModel.create(service,draft);setPlan(next);setSaved(structuredClone(next));setPublished(structuredClone(next));const from={bitrix:'J03',amo:'Q04',mindbox:'D04'}[service];setOrigin(from);setOriginConnection(scope(from));go('X01');},
      add: (parent = null, slot = null) => { setSelection({ parent, slot, id: null, kind: 'action' }); go('X02'); },
      choose: kind => { setSelection(old => ({ ...old, kind })); go(kind === 'action' ? 'X03' : 'X05'); },
      edit: (step, parent, slot) => { setSelection({ id: step.id, kind: step.kind, parent, slot }); go(step.kind === 'action' ? 'X03' : 'X05'); },
      apply: step => { editList(steps => { const list = M.siblings(steps, selection.parent, selection.slot); const index = list.findIndex(s => s.id === selection.id);
        if (index < 0) list.push(step); else list[index] = step; }); go('X01'); },
      reorder: (id, parent, slot, before) => editList(steps => {
        const list = M.siblings(steps, parent, slot), index = list.findIndex(s => s.id === id);
        if (index < 0 || id === before || (before !== null && !list.some(s => s.id === before))) return;
        const [step] = list.splice(index, 1);
        list.splice(before === null ? list.length : list.findIndex(s => s.id === before), 0, step);
      }),
      manipulate: (id, parent, slot, action) => editList(steps => {
        const list = M.siblings(steps, parent, slot), index = list.findIndex(s => s.id === id);
        if (action === 'remove') list.splice(index, 1);
        if (action === 'copy') list.splice(index + 1, 0, M.cloneStep(list[index]));
        const target = index + (action === 'up' ? -1 : 1);
        if (['up','down'].includes(action) && target >= 0 && target < list.length) [list[index], list[target]] = [list[target], list[index]];
      }),
      save: () => { setSaved(structuredClone(plan)); go('X07'); },
      copy: () => { const copy = { ...structuredClone(plan), name: window.jt('copyName').replace('{name}',plan.name || window.jt('customTitle')) };
        setArchived(old=>[...old,{plan:structuredClone(saved || plan),published:structuredClone(published),origin,originConnection}]);
        setPlan(copy); setSaved(null); setPublished(null); go('X01'); },
      openArchived: index => { const item=archived[index];archiveCurrent();setPlan(structuredClone(item.plan));setSaved(structuredClone(item.plan));setPublished(item.published);setOrigin(item.origin);setOriginConnection(item.originConnection);go('X01'); },
      restore: () => setPlan(structuredClone(saved || M.blank())),
      enable: () => { if (!M.errors(plan).length) { setSaved(structuredClone(plan)); setPublished(structuredClone(plan)); go('X07'); } },
      leave: () => go(dirty ? 'X09' : origin),
      saveLeave: () => { setSaved(structuredClone(plan)); go(origin); },
      discardLeave: () => { setPlan(structuredClone(saved || M.blank())); go(origin); },
    };
    return h(Context.Provider, { value }, children);
  }
  window.Custom = { Provider, use: () => R.useContext(Context) };
})();
