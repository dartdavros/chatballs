// Object and list values are entered with fields, without JSON or code.
(function () {
  const {h,text}=window.ServiceParts,W=window.Workbench,t=window.jt;let sequence=0;
  function ObjectValue({value:v,onChange}){
    const fields=v.fields || [],set=fields=>onChange({...v,fields,value:fields.length?'object-value':''});
    return h('div',{className:'si-form-section'},...fields.map((field,index)=>h('div',{className:'si-nested',key:field.id},
      h(W.Field,{label:'fieldName',value:field.name,onChange:name=>set(fields.map((old,i)=>i===index?{...old,name}:old))}),
      h(W.Select,{label:'fieldType',value:field.type,options:window.SchemaEditor.types.map(type=>[type,window.SchemaEditor.label(type)]),onChange:type=>set(fields.map((old,i)=>i===index?{...old,type,binding:{source:'constant',value:''}}:old))}),
      h(window.BindingEditor,{value:field.binding,expected:field.type,onChange:binding=>set(fields.map((old,i)=>i===index?{...old,binding}:old))}),
      h(W.Button,{label:'removeParameter',icon:'trash',onClick:()=>set(fields.filter((_,i)=>i!==index))}))),
      h(W.Button,{label:'addNested',icon:'plus',onClick:()=>set([...fields,{id:`constant-${++sequence}`,name:'',type:'text',binding:{source:'constant',value:''}}])}));
  }
  function ListValue({value:v,onChange}){
    const items=v.items || [],set=items=>onChange({...v,items,value:items.length?'list-value':''});
    return h('div',{className:'si-form-section'},h(W.Select,{label:'listItemType',value:v.itemType || 'text',options:window.SchemaEditor.types.filter(type=>type!=='list').map(type=>[type,window.SchemaEditor.label(type)]),onChange:itemType=>onChange({...v,itemType,items:[],value:''})}),
      ...items.map((item,index)=>h('div',{className:'si-nested',key:item.id},text('strong',t('listItem').replace('{number}',String(index+1))),
        h(window.BindingEditor,{value:item.binding,expected:v.itemType || 'text',onChange:binding=>set(items.map((old,i)=>i===index?{...old,binding}:old))}),
        h(W.Button,{label:'removeParameter',icon:'trash',onClick:()=>set(items.filter((_,i)=>i!==index))}))),
      h(W.Button,{label:'addListItem',icon:'plus',onClick:()=>set([...items,{id:`constant-${++sequence}`,binding:{source:'constant',value:''}}])}));
  }
  window.ConstantValues={ObjectValue,ListValue};
})();
