// Declared values of a parameter, edited as fields rather than source code.
(function(){
  const {h}=window.ServiceParts,W=window.Workbench;
  function Choices({value:v,onChange}){
    const choices=v.choices || [],set=choices=>onChange({...v,choices});
    return h('div',{className:'si-form-section'},h(W.Toggle,{inline:true,label:'restrictChoices',checked:!!v.limited,onChange:limited=>onChange({...v,limited})}),
      v.limited && h('div',{className:'si-nested si-form-section'},...choices.map((value,index)=>h('div',{className:'si-mapping-row',key:index},
        h(W.Field,{label:'allowedChoice',type:v.type==='number'?'number':'text',value,onChange:value=>set(choices.map((old,i)=>i===index?value:old))}),
        h(W.Button,{label:'removeAllowedChoice',icon:'trash',onClick:()=>set(choices.filter((_,i)=>i!==index))}))),
        h(W.Button,{label:'addAllowedChoice',icon:'plus',onClick:()=>set([...choices,''])})));
  }
  const valid=v=>!['text','number'].includes(v.type) || !v.limited || !!v.choices?.length && v.choices.every(value=>value.trim()) && new Set(v.choices).size===v.choices.length;
  window.ParameterChoices={Choices,valid};
})();
