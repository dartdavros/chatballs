(function(){
  const t=window.jt;
  function describe(value,steps=[],inputs=[]){
    if(!value?.value)return t('noValueConfigured');
    if(value.source==='constant'){
      if(value.fields)return value.fields.map(field=>`${field.name}: ${describe(field.binding,steps,inputs)}`).join('; ');
      if(value.items)return value.items.map(item=>describe(item.binding,steps,inputs)).join('; ');
      return value.value==='inputFiles'?t('attachmentInput'):value.value==='true'?t('yesValue'):value.value==='false'?t('noValue'):value.value;
    }
    if(value.source==='step'){
      const index=steps.findIndex(step=>step.id===value.value);if(index<0)return t('missingSource');
      const fields=window.StepResults(steps[index]),field=fields.find(field=>field[0]===value.field) || fields[0];
      return t('sourceStepDescription').replace('{number}',String(index+1)).replace('{field}',t(field?.[1] || 'recordId'));
    }
    if(value.source==='input')return t('inputSummary').replace('{value}',inputs.find(input=>input.id===value.value)?.name || value.value);
    if(value.source==='context')return t('contextSummary').replace('{value}',t(value.value));
    return `${t({event:'valueEvent',directory:'valueDirectory',iteration:'valueIteration'}[value.source])} → ${t(value.value)}`;
  };
  window.ValueSummary=(value,...args)=>{const result=describe(value,...args);return value?.transform && value.transform!=='none'?`${result} → ${window.Transformation.summary(value)}`:result;};
})();
