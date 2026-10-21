// Reusable ordered list. Reordering stays inside its branch so data scopes remain explicit.
(function () {
  const { h, text } = window.ServiceParts, U = window.ServiceUI, M = window.CustomModel, t = window.jt;
  const title = step => step.kind === 'action' ? t(M.operations[step.service].find(op => op[0] === step.operation)[1]) : t(M.kinds.find(k => k[0] === step.kind)[1]);
  function summary(step, siblings = [],inputs=[]) {
    if (step.kind !== 'action') {
      const p = step.params;
      if (step.kind === 'branch') return p.condition === 'tag' ? `${t('conditionTag')}: ${p.tag || ''}` : t('contactPresent');
      if (step.kind === 'delay') return p.mode === 'date' ? `${t('dateMode')}: ${p.date}` : t('delaySummary').replace('{value}', p.minutes || '');
      if (step.kind === 'approval') return p.message;
      return t(M.kinds.find(k => k[0] === step.kind)[2]);
    }
    const op = M.operations[step.service].find(o => o[0] === step.operation);
    if (op[3] === 'linked') return t('mindboxData');
    const value=window.ValueSummary(step,siblings,inputs);
    return `${t(op[2])}: ${value}`;
  }
  function Steps({ steps, parent = null, slot = null, prefix = '' }) {
    const c = window.Custom.use(), R = window.React;
    const [dragged, setDragged] = R.useState(null), [before, setBefore] = R.useState(undefined), [announcement, announce] = R.useState('');
    const dragging = R.useRef(null);
    const end = () => { dragging.current = null; setDragged(null); setBefore(undefined); };
    const drop = event => {
      if (!dragging.current) return;
      event.preventDefault(); event.stopPropagation();
      if (before !== undefined) c.reorder(dragging.current, parent, slot, before);
      announce(t('stepMoved')); end();
    };
    const insertion = id => h('div', { key: `drop-${id}`, className: `si-drop-slot${dragged && before === id ? ' is-target' : ''}`, 'aria-hidden': true });
    const rows = steps.flatMap((step, index) => [insertion(step.id), h('section', {
      key: step.id, 'data-step-id': step.id, className: `si-block si-sortable${dragged === step.id ? ' is-dragging' : ''}`,
      onDragOver: event => {
        if (!dragging.current) return;
        event.preventDefault(); event.stopPropagation(); event.dataTransfer.dropEffect = 'move';
        const rect = event.currentTarget.getBoundingClientRect();
        setBefore(event.clientY < rect.top + rect.height / 2 ? step.id : (steps[index + 1]?.id || null));
      }, onDrop: drop,
    }, h('header', null,
      h('button', { type: 'button', className: 'site-field-grip', draggable: true,
        'aria-label': `${t('reorderStep')}: ${prefix}${index + 1}`, title: t('reorderHelp'),
        onDragStart: event => {
          event.stopPropagation(); dragging.current = step.id; setDragged(step.id);
          event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', step.id);
          const preview = event.currentTarget.closest('section'); preview.classList.add('is-dragging');
          event.dataTransfer.setDragImage(preview, 24, 24);
        }, onDragEnd: end,
        onKeyDown: event => {
          if (['ArrowUp','ArrowDown'].includes(event.key)) {
            event.preventDefault(); c.manipulate(step.id, parent, slot, event.key === 'ArrowUp' ? 'up' : 'down'); announce(t('stepMoved'));
          }
        },
      }, h(U.Icon, { name: 'grip', size: 14 })),
      text('span', `${prefix}${index + 1}`, 'si-step-number'),
      h('div', null, h('div', { className: 'journey-step-title' }, text('h3', title(step)),
        step.kind === 'action' && (step.service === 'chatballs' ? text('span', t('chatballs'), 'si-muted') : h(window.ServiceLogo, { service: step.service, compact: true }))),
        text('p', summary(step, steps,c.plan.inputs))),
      h('div', { className: 'si-step-actions' },
        h(U.Button, { variant: 'secondary', icon: 'edit', 'aria-label': `${t('editStep')}: ${prefix}${index + 1}`, onClick: () => c.edit(step, parent, slot) }, t('editStep')),
        h(U.Dropdown, { trigger: ['click'], overlayClassName: 'app-dropdown', menu: { items: [
          { key: 'copy', icon: h(U.Icon, { name: 'copy', size: 15 }), label: t('duplicate'), onClick: () => c.manipulate(step.id, parent, slot, 'copy') },
          { key: 'remove', icon: h(U.Icon, { name: 'trash', size: 15 }), label: t('removeStep'), danger: true, onClick: () => c.manipulate(step.id, parent, slot, 'remove') },
        ] } }, h('button', { className: 'row-menu-button', type: 'button', 'aria-label': `${t('stepActions')}: ${prefix}${index + 1}` }, h(U.Icon, { name: 'more', size: 16 }))))),
      Object.keys(step.children).length > 0 && h('div', { className: 'si-block-body' }, ...Object.entries(step.children).map(([key, list], branchIndex) =>
        h('div', { key, className: 'si-nested' }, text('h3', t(key)), h(Steps, { steps: list, parent: step.id, slot: key, prefix: `${prefix}${index + 1}.${branchIndex + 1}.` })))))]);
    return h('div', { className: 'si-step-list', onDrop: drop }, ...rows, insertion(null),
      h(U.Button, { variant: 'secondary', icon: 'plus', onClick: () => c.add(parent, slot),
        onDragOver: event => { if (dragging.current) { event.preventDefault(); event.stopPropagation(); setBefore(null); } } }, t('customAdd')),
      h('span', { className: 'si-sr-only', role: 'status', 'aria-live': 'polite' }, announcement));
  }
  function Summary({ steps }) {
    const c=window.Custom.use();
    return h('ol', { className: 'si-review-steps' }, ...steps.map(step => h('li', { key: step.id }, text('strong', title(step)), text('p', summary(step, steps,c.plan.inputs)),
      ...Object.entries(step.children).map(([key, list]) => h('div', { key, className: 'si-nested' }, text('strong', t(key)), h(Summary, { steps: list }))))));
  }
  window.CustomSteps = { Steps, Summary, title, summary };
})();
