(function () {
  const { h, text, card } = window.ServiceParts, W = window.Workbench, t = window.jt;
  let id = 0;
  const rule = () => ({ id: `condition-${++id}`, field: 'contact', value: '' });
  const group = () => ({ id: `condition-group-${++id}`, mode: 'all', rules: [rule()] });
  function Group({ value: v, onChange, removable, onRemove }) {
    const setRule = (index, value) => onChange({ ...v, rules: v.rules.map((old,i) => i === index ? value : old) });
    return h('div',{className:'si-form-section'},h(W.Select,{label:'conditionMode',value:v.mode,options:[['all','allConditions'],['any','anyCondition']],onChange:mode=>onChange({...v,mode})}),
      ...v.rules.map((r,index)=>h('div',{className:'si-nested',key:r.id},r.rules ? h(Group,{value:r,onChange:value=>setRule(index,value),removable:true,onRemove:()=>onChange({...v,rules:v.rules.filter((_,i)=>i!==index)})})
        : h('div',{className:'si-form-section'},h(W.Select,{label:'checkField',value:r.field,options:[['contact','contactPresent'],['tag','conditionTag']],onChange:field=>setRule(index,{...r,field})}),
          r.field==='tag' && h(W.Field,{label:'conditionValue',value:r.value,onChange:value=>setRule(index,{...r,value})}),
          h(W.Button,{label:'removeCondition',icon:'trash',onClick:()=>onChange({...v,rules:v.rules.filter((_,i)=>i!==index)})})))),
      h('div',{className:'server-actions si-actions'},h(W.Button,{label:'addCondition',icon:'plus',onClick:()=>onChange({...v,rules:[...v.rules,rule()]})}),
        h(W.Button,{label:'addConditionGroup',onClick:()=>onChange({...v,rules:[...v.rules,group()]})})),
      removable && h(W.Button,{label:'removeConditionGroup',onClick:onRemove}));
  }
  const invalid = v => v.rules.some(r => r.rules ? invalid(r) : r.field==='tag' && !r.value.trim());
  function Conditions() {
    const c = window.Custom.use(), R = window.React;
    const [v,set] = R.useState(()=>structuredClone(c.plan.conditions || {id:'root',mode:'all',rules: c.plan.condition==='none'?[]:[{id:'original',field:c.plan.condition,value:c.plan.tag}]}));
    return h('div',{className:'si-card-body'},card(t('conditions'),h(W.Help,{label:'conditionsLead'}),
      !v.rules.length && text('p',t('customConditionEmpty')),h(Group,{value:v,onChange:set})),
      h(W.Footer,{disabled:invalid(v),onApply:()=>{c.update({conditions:v,condition:v.rules.length ? v.rules[0].rules?'group':v.rules[0].field:'none',tag:v.rules[0]?.value || ''});c.go('X01');}}));
  }
  function Summary({ value }) {
    return value?.rules.length ? h('div',null,text('strong',t(value.mode==='all'?'allConditions':'anyCondition')),
      h('ul',null,...value.rules.map(r=>h('li',{key:r.id},r.rules?h(Summary,{value:r}):r.field==='tag'?`${t('conditionTag')}: ${r.value}`:t('contactPresent'))))) : text('p',t('customConditionEmpty'));
  }
  window.ConditionEditor = { Conditions, Summary, invalid };
})();
