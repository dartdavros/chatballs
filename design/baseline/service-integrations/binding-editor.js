// One value-source control reused by action parameters and scenario results.
(function () {
  const { h, text } = window.ServiceParts, W = window.Workbench, t = window.jt;
  const transforms = { text: ['none','trim','text','join'], number: ['none','number'], date: ['none','date'], datetime: ['none','date'], object: ['none','object'], list: ['none','list'], file: ['none'], directory: ['none'], boolean: ['none'] };
  const transformLabels = { none: 'noTransform', trim: 'trimText', text: 'toText', number: 'toNumber', join: 'joinText', date: 'dateZone', object: 'objectFields', list: 'listFilter' };
  const valid = (v,expected,steps=[],inputs=[]) => {
    if(!v.value)return true;
    if(!window.Transformation.valid(v))return false;
    if(v.transform && v.transform!=='none')return true;
    if(v.source==='constant'){
      if(expected==='number')return Number.isFinite(Number(v.value));
      if(['date','datetime'].includes(expected))return Number.isFinite(Date.parse(v.value));
      if(expected==='boolean')return ['true','false'].includes(v.value);
      if(expected==='object')return !!v.fields?.length && v.fields.every(field=>field.name.trim() && field.binding.value && valid(field.binding,field.type,steps,inputs));
      if(expected==='list')return !!v.items?.length && v.items.every(item=>item.binding.value && valid(item.binding,v.itemType || 'text',steps,inputs));
      return true;
    }
    const result=window.StepResults(steps.find(step=>step.id===v.value)),type=v.source==='step'?(result.find(field=>field[0]===v.field) || result[0])?.[2]
      :v.source==='input'?inputs.find(input=>input.id===v.value)?.type || 'text':v.value==='eventTime'?'datetime':v.value==='iterationFile'?'file':'text';
    return type===expected || expected==='directory' && type==='text';
  };
  function Binding({ value: v, onChange, expected = 'text', previous, inLoop = false, label = 'paramValue', nullable = false }) {
    const c = window.Custom.use(), M = window.CustomModel;
    const set = patch => onChange({ ...v, ...patch });
    const prior = previous || c.plan.steps;
    const sources = [['constant','valueConstant'],['context','valueContext'],['input','valueInput'],['event','valueEvent'],['directory','valueDirectory'],['step','valueResult'], ...(inLoop ? [['iteration','valueIteration']] : [])];
    const options = {
      context: [['contextTitle','contextTitle'],['contextId','contextId'],['contextContact','contextContact']],
      event: [['eventTitle','eventTitle'],['eventTime','eventTime']],
      directory: [['stageValue','stageValue'],['memberAnna','memberAnna'],['memberDmitry','memberDmitry']],
      iteration: [['iterationFile','iterationFile'],['iterationName','iterationName']],
      input: c.plan.inputs.map(p => [p.id,p.name]),
      step: prior.map((s,index) => [s.id, `${index + 1}. ${window.CustomSteps.title(s)}`]),
    };
    let control;
    if(v.source==='constant' && expected==='object')control=h(window.ConstantValues.ObjectValue,{value:v,onChange});
    else if(v.source==='constant' && expected==='list')control=h(window.ConstantValues.ListValue,{value:v,onChange});
    else if(v.source==='constant' && expected==='boolean')control=h(W.Select,{label,value:v.value || '',options:[['true','yesValue'],['false','noValue']],onChange:value=>set({value})});
    else if (v.source === 'constant' && expected === 'file') control = h(W.Select, { label: 'selectedFiles', value: v.value || '', options: [['inputFiles','attachmentInput']], onChange: value => set({ value }) });
    else if (v.source === 'constant') control = h(W.Field, { label, value: v.value || '', type: expected === 'number' ? 'number' : expected === 'date' ? 'date' : expected === 'datetime' ? 'datetime-local' : 'text', onChange: value => set({ value }) });
    else if (v.source === 'input' && !c.plan.inputs.length) control = h('div', { className: 'si-form-section' }, h(W.Field, { label: 'inputLabel', value: v.value || '', onChange: value => set({ value }) }), h(W.Help, { label: 'dataHelpInput' }));
    else control = h(W.Select, { label: 'sourceField', value: v.value || '', options: options[v.source] || [], onChange: value => set({ value }) });
    return h('div', { className: 'si-form-section' }, h(W.Select, { label: 'paramSource', value: v.source, options: sources, onChange: source => onChange({ source, value: '', transform: 'none', absent: 'stop' }) }),
      control, v.source==='step' && v.value && h(W.Select,{label:'resultField',value:v.field || window.StepResults(prior.find(s=>s.id===v.value))[0]?.[0],
        options:window.StepResults(prior.find(s=>s.id===v.value)).map(([key,label])=>[key,label]),onChange:field=>set({field})}),
      h(W.Select, { label: 'transform', value: v.transform || 'none', options: (transforms[expected] || transforms.text).map(key => [key,transformLabels[key]]), onChange: transform => set({ transform,transformOptions:{} }) }),
      h(window.Transformation.Settings,{value:v,onChange}),
      h(W.Select, { label: 'absentValue', value: v.absent || 'stop', options: [['stop','stopValue'],['omit','omitValue'],...(nullable?[['null','nullValue']]:[])], onChange: absent => set({ absent }) }),
      !valid(v,expected,prior,c.plan.inputs) && text('small',t(expected==='number'?'bindingTypeError':'bindingTypeMismatch'),'form-field-error'),
      v.source==='context' && !c.plan.launch.manual && !c.plan.launch.ai && !c.plan.launch.internal && text('small',t('contextUnavailable'),'form-field-error'),
      h(W.Help, { label: 'transformHelp' }));
  }
  window.BindingEditor = Binding;
  window.BindingValid = valid;
  window.ActionBindingTypes={customerName:'text',customerEmail:'text',untilTime:'datetime',paramAmount:'number',attachments:'file'};
})();
