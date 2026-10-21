(function () {
  const { h, text, card } = window.ServiceParts, W = window.Workbench, t = window.jt;
  let sequence = 0;
  const create = () => ({ id: `parameter-${++sequence}`, name: '', type: 'text', required: true, nullable: false, itemType: 'file', children: [] });
  const types = ['text','number','boolean','date','datetime','object','list','directory','file'];
  const label = type => `type${type[0].toUpperCase()}${type.slice(1)}`;
  function Parameter({ value: v, onChange, onRemove, result }) {
    const set = patch => onChange({ ...v, ...patch });
    return card('', h('div', { className: 'si-parameter-head' },
      h(W.Field, { label: 'fieldName', value: v.name, onChange: name => set({ name }) }),
      h(window.ServiceUI.Dropdown, { trigger: ['click'], overlayClassName: 'app-dropdown', menu: { items: [
        { key: 'remove', danger: true, label: t('removeParameter'), onClick: onRemove },
      ] } }, h('button', { className: 'row-menu-button', type: 'button', 'aria-label': t('parameterActions') }, h(window.ServiceUI.Icon, { name: 'more', size: 16 })))),
      h(W.Select, { label: 'fieldType', value: v.type, options: types.map(type => [type,label(type)]), onChange: type => set({ type }) }),
      h(W.Toggle, { inline:true,label: 'requiredField', checked: v.required, onChange: required => set({ required }) }),
      h(W.Toggle, { inline:true,label: 'nullableField', checked: v.nullable, onChange: nullable => set({ nullable }) }),
      ['text','number'].includes(v.type) && h(window.ParameterChoices.Choices,{value:v,onChange}),
      !result && v.type === 'list' && h(W.Select, { label: 'listItemType', value: v.itemType, options: types.filter(type => type !== 'list').map(type => [type,label(type)]), onChange: itemType => set({ itemType }) }),
      v.type === 'directory' && h(W.Select, { label: 'directoryChoice', value: 'stages', options: [['stages','directoryStages']], onChange: () => {} }),
      v.type === 'file' && h(W.Help, { label: 'fileAccessHelp' }),
      !result && (v.type === 'object' || v.type === 'list' && v.itemType === 'object') && h('div', { className: 'si-nested' }, text('strong', t('nestedFields')),
        h(List, { values: v.children, onChange: children => set({ children }), nested: true })),
      result && h(window.BindingEditor, { value: v.binding || { source: 'step', value: '' }, onChange: binding => set({ binding }), expected: v.type, nullable:v.nullable }));
  }
  function List({ values, onChange, nested, result }) {
    return h('div', { className: 'si-card-body' }, ...values.map((v, index) => h(Parameter, { key: v.id, value: v, result,
      onChange: value => onChange(values.map((old, i) => i === index ? value : old)), onRemove: () => onChange(values.filter((_, i) => i !== index)) })),
      h(W.Button, { label: nested ? 'addNested' : result ? 'addResult' : 'addParameter', icon: 'plus', onClick: () => onChange([...values, create()]) }));
  }
  const invalid = values => values.some(v => !v.name.trim() || values.filter(other => other.name.trim() === v.name.trim()).length > 1 || !window.ParameterChoices.valid(v) || invalid(v.children));
  function Schema() {
    const c = window.Custom.use(), R = window.React;
    const [inputs, setInputs] = R.useState(() => structuredClone(c.plan.inputs)), [outputs, setOutputs] = R.useState(() => structuredClone(c.plan.outputs)), [submitted, submit] = R.useState(false);
    const error = invalid(inputs) || invalid(outputs);
    return h('div', { className: 'si-card-body' }, h(W.Tabs, { active: 'X10' }),
      card(t('inputSchema'), h(W.Help, { label: 'inputSchemaHelp' }), !inputs.length && h(W.Help, { label: 'emptyParameters' }), h(List, { values: inputs, onChange: setInputs })),
      card(t('outputSchema'), h(W.Help, { label: 'outputSchemaHelp' }), h(List, { values: outputs, onChange: setOutputs, result: true })),
      submitted && error && text('small', t('schemaNameRequired'), 'form-field-error'),
      h(W.Footer, { onApply: () => { submit(true); if (!error) { c.update({ inputs, outputs }); c.go('X01'); } } }));
  }
  window.SchemaEditor = { Schema, List, invalid, types, label };
})();
