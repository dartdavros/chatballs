(function () {
  const { h, U, t, text, icon, field, select } = window.EventParts;
  // Item/button structure from integrations/rows.tsx (RowActions).
  function FieldActions({onRemove}) {
    const [open,setOpen]=window.React.useState(false);
    return h(U.Dropdown,{open,onOpenChange:setOpen,trigger:['click'],overlayClassName:'app-dropdown',menu:{items:[
      {key:'remove',label:h('button',{type:'button',className:'warning',onClick:()=>{setOpen(false);onRemove();}},
        h(U.Icon,{name:'trash',size:15}),t('removeField'))},
    ]}},h('button',{type:'button',className:'row-menu-button','aria-label':t('actions')},icon('more')));
  }
  function Schema({ values, onChange }) {
    return h('section', { className: 'site-fields-card ev-schema' },
      h('div',{className:'site-fields-card-head'},text('strong','schema'),
        h(U.Button,{variant:'primary',icon:'plus',onClick:()=>onChange([...values,{name:'',type:'text',limit:'120',min:'0',max:'100',required:false}])},t('addField'))),
      h('div',{className:'ev-schema-scroll',tabIndex:0,role:'region','aria-label':t('schema')},
      h('table',{className:'site-fields-table ev-schema-table'},
      h('thead',null,h('tr',null,...['fieldName','fieldType','limits','required','actions'].map(key=>text('th',key,{key,scope:'col',className:key==='actions'?'ev-actions-heading':undefined})))),
      h('tbody',null,...values.map((v, index) => {
        const set = patch => onChange(values.map((old,i) => i === index ? { ...old, ...patch } : old));
        return h('tr', { key: index, className: 'ev-schema-row' },
          h('td',{className:'ev-cell-unlabelled'},field('fieldName',v.name,name=>set({name}),{mono:true})),
          h('td',{className:'ev-cell-unlabelled'},select('fieldType',v.type,type=>set({type}),[['text','textType'],['number','numberType'],['boolean','booleanType']])),
          h('td',{className:'ev-schema-limits'},v.type==='text'?field('maxLength',v.limit,limit=>set({limit}),{type:'number'}):
            v.type==='number'?h('div',{className:'ev-range'},
              field('minimum',v.min,min=>set({min}),{type:'number'}),field('maximum',v.max,max=>set({max}),{type:'number'})):h('span',{'aria-hidden':true},'—')),
          h('td',null,h(U.SwitchButton,{label:t('required'),checked:v.required,onClick:()=>set({required:!v.required}),className:'ui-switch is-compact'})),
          h('td',null,h(FieldActions,{onRemove:()=>onChange(values.filter((_,i)=>i!==index))})));
      })))),text('div','schemaHelp',{className:'site-fields-footer'}));
  }
  window.EventSchema = Schema;
})();
