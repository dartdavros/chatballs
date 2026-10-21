// Design-only state and tree operations. No execution engine or API calls.
(function () {
  const kinds = [
    ['action', 'customAction', 'customActionHelp', []], ['branch', 'customBranch', 'customBranchHelp', ['yesBranch', 'noBranch']],
    ['each', 'customEach', 'customEachHelp', ['eachBody']], ['parallel', 'customParallel', 'customParallelHelp', ['parallelOne', 'parallelTwo']],
    ['nested', 'customNested', 'customNestedHelp', []], ['delay', 'customDelay', 'customDelayHelp', []],
    ['event', 'customEvent', 'customEventHelp', []], ['approval', 'customApproval', 'customApprovalHelp', []],
    ['try', 'customTry', 'customTryHelp', ['tryBody', 'catchBody']],
  ];
  const operations = {
    bitrix: [['lead', 'actionLead', 'paramLead', 'text']], amo: [['deal', 'actionDeal', 'paramDeal', 'text']],
    mindbox: [['customer', 'actionCustomer', 'paramCustomer', 'linked']],
    chatballs: [['tag', 'actionTag', 'paramTag', 'text'], ['assign', 'actionAssign', 'paramEmployee', 'employee'],
      ['notify', 'actionNotify', 'paramMessage', 'text'], ['link', 'actionLink', 'paramRecord', 'record']],
  };
  const blank = () => ({ name: '', group: 'support', condition: 'none', tag: '', steps: [], inputs: [], outputs: [],
    launch: window.LaunchModel.defaults(), sync: window.SyncSettings.defaults() });
  let sequence = 0;
  const makeStep = kind => ({ id: `step-${++sequence}`, kind, service: 'chatballs', operation: 'tag', source: 'constant', value: '',
    params: {}, children: Object.fromEntries(kinds.find(x => x[0] === kind)[3].map(slot => [slot, []])) });
  const visit = (steps, id) => {
    for (const step of steps) { if (step.id === id) return step; for (const list of Object.values(step.children)) { const found = visit(list, id); if (found) return found; } }
  };
  const siblings = (steps, parent, slot) => parent ? visit(steps, parent).children[slot] : steps;
  const cloneStep = step => {
    const ids = new Map();
    const copy = node => {
      const id = `step-${++sequence}`; ids.set(node.id, id);
      return { ...structuredClone(node), id, children: Object.fromEntries(Object.entries(node.children).map(([key, list]) => [key, list.map(copy)])) };
    };
    const result = copy(step);
    const remap = node => {
      if (node.source === 'step' && ids.has(node.value)) node.value = ids.get(node.value);
      Object.values(node.bindings || {}).forEach(binding=>{if(binding.source==='step' && ids.has(binding.value))binding.value=ids.get(binding.value);});
      Object.values(node.children).flat().forEach(remap);
    };
    remap(result); return result;
  };
  const invalidBlock = step => {
    const p = step.params;
    if (step.kind === 'delay' && p.mode === 'date') return !p.date || !Number.isFinite(Date.parse(p.date));
    if (['delay','event','approval'].includes(step.kind) && !(Number(p.minutes) > 0)) return true;
    if (step.kind === 'approval' && !p.message?.trim()) return true;
    return step.kind === 'branch' && p.condition === 'tag' && !p.tag?.trim();
  };
  const errors = plan => {
    const result = [];
    if (!plan.name.trim()) result.push('customNameError');
    if (!plan.steps.length) result.push('customStepsError');
    if (plan.condition === 'tag' && !plan.tag.trim()) result.push('customParameterError');
    result.push(...window.LaunchModel.errors(plan.launch));
    const dialogContext=plan.launch.manual || plan.launch.ai || plan.launch.internal;
    if(!dialogContext && plan.condition!=='none')result.push('contextUnavailable');
    if (window.SchemaEditor.invalid(plan.inputs) || window.SchemaEditor.invalid(plan.outputs)) result.push('schemaNameRequired');
    const check = steps => steps.forEach((step, index) => {
      if (step.kind === 'action' && step.service !== 'mindbox' && !step.value.trim()) result.push('customParameterError');
      if(!dialogContext && (step.source==='context' || Object.values(step.bindings || {}).some(binding=>binding.source==='context')))result.push('contextUnavailable');
      if (step.kind === 'action' && step.source === 'step' && !steps.slice(0, index).some(s => s.id === step.value && s.kind === 'action' && ['lead', 'deal', 'customer'].includes(s.operation))) result.push('customDependencyError');
      if (invalidBlock(step)) result.push('customParameterError');
      if(Object.entries(step.bindings || {}).some(([key,binding])=>!window.BindingValid(binding,window.ActionBindingTypes[key],steps.slice(0,index),plan.inputs)))result.push('bindingTypeMismatch');
      if(Object.values(step.bindings || {}).some(binding=>binding.source==='step' && !steps.slice(0,index).some(previous=>previous.id===binding.value)))result.push('customDependencyError');
      for (const list of Object.values(step.children)) { if (!list.length) result.push('customChildError'); check(list); }
    });
    check(plan.steps);
    if(plan.outputs.some(output=>output.required && !output.binding?.value))result.push('outputRequired');
    if(plan.outputs.some(output=>output.binding && !window.BindingValid(output.binding,output.type,plan.steps,plan.inputs)))result.push('bindingTypeMismatch');
    return [...new Set(result)];
  };
  window.CustomModel = { kinds, operations, blank, makeStep, visit, siblings, cloneStep, invalidBlock, errors };
})();
