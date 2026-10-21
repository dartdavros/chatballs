// Reusable configuration for the typed transformations declared by the specification.
(function(){
  const {h}=window.ServiceParts,W=window.Workbench,t=window.jt;
  const labels={trim:'trimText',text:'toText',number:'toNumber',join:'joinText',date:'dateZone',object:'objectFields',list:'listFilter'};
  function Settings({value:v,onChange}){
    const p=v.transformOptions || {},set=patch=>onChange({...v,transformOptions:{...p,...patch}});
    if(!v.transform || v.transform==='none')return null;
    const fields={
      number:()=>h(W.Select,{label:'numberSeparator',value:p.decimal || 'dot',options:[['dot','decimalDot'],['comma','decimalComma']],onChange:decimal=>set({decimal})}),
      join:()=>h(W.Field,{label:'joinSeparator',value:p.separator ?? ', ',onChange:separator=>set({separator})}),
      date:()=>h(W.Select,{label:'targetZone',value:p.zone || 'Europe/Moscow',options:[['Europe/Moscow','zoneMoscow'],['Europe/Berlin','zoneBerlin']],onChange:zone=>set({zone})}),
      object:()=>h('div',{className:'si-form-section'},...(p.fields || []).map((name,index)=>h('div',{className:'si-mapping-row',key:index},
        h(W.Field,{label:'selectedObjectField',value:name,onChange:name=>set({fields:p.fields.map((old,i)=>i===index?name:old)})}),
        h(W.Button,{label:'removeSelectedField',icon:'trash',onClick:()=>set({fields:p.fields.filter((_,i)=>i!==index)})}))),
        h(W.Button,{label:'addSelectedField',icon:'plus',onClick:()=>set({fields:[...p.fields || [],'']})})),
      list:()=>h('div',{className:'si-form-section'},h(W.Field,{label:'filterItemField',value:p.field || '',onChange:field=>set({field})}),
        h(W.Select,{label:'filterOperator',value:p.operator || 'filled',options:[['filled','filterFilled'],['equals','filterEquals'],['contains','filterContains']],onChange:operator=>set({operator})}),
        p.operator && p.operator!=='filled' && h(W.Field,{label:'filterValue',value:p.value || '',onChange:value=>set({value})})),
    };
    return fields[v.transform]?h('div',{className:'si-nested si-form-section'},fields[v.transform]()):null;
  }
  const valid=v=>v.transform==='object' ? !!v.transformOptions?.fields?.length && v.transformOptions.fields.every(name=>name.trim())
    :v.transform==='list' ? !!v.transformOptions?.field?.trim() && (!v.transformOptions.operator || v.transformOptions.operator==='filled' || !!v.transformOptions.value?.trim()):true;
  const summary=v=>{const p=v.transformOptions || {},extra=v.transform==='date'?(p.zone || 'Europe/Moscow'):v.transform==='join'?(p.separator ?? ', ')
    :v.transform==='object'?(p.fields || []).join(', '):v.transform==='list'?`${p.field || ''} · ${t({filled:'filterFilled',equals:'filterEquals',contains:'filterContains'}[p.operator || 'filled'])}${p.value?` ${p.value}`:''}`:'';
    return `${t(labels[v.transform])}${extra?`: ${extra}`:''}`;};
  window.Transformation={Settings,valid,summary};
})();
