(function () {
  const {h,t,text,icon} = window.EventParts, P=window.SpeechProduct, E=window.EventProduct;
  const accent='#0f9b8e';
  function Panel({ state:s,dispatch,width }) {
    const [expanded,setExpanded]=window.React.useState(false);
    const ref=window.React.useRef(null), consent=['consent','stale','late'].includes(s.phase);
    const config={available:true,autonomous:true,greeting:t('greeting'),consent:{text:`<p>${t('consent')}</p>`,version:s.phase==='stale'?'2':'1'},
      preChat:{enabled:true,title:t('formTitle'),fields:[{key:'name',required:true}]}};
    const form=s.phase==='form';
    return h('div',{className:`ev-panel${expanded?' is-expanded':''}`,role:'region','aria-label':t('header')},h('div',{className:'cb-widget'},
      h(E.ChatHeader,{accent,title:t('header'),expanded,canExpand:width>480,onToggleExpand:()=>setExpanded(!expanded),onClose:()=>dispatch({type:'open'})}),
      form ? h(P.PreChatForm,{config,accent,title:t('header'),siteValues:{},starting:false,onAccept:async()=>dispatch({type:'consent'})})
        : consent ? h(window.React.Fragment,null,
          h(E.ChatBody,{bodyRef:ref,config,unavailable:false,accepted:false,accent,title:t('header'),messages:[],pending:[],awaiting:false,lastContactRequestId:0,showPhoneForm:false,onSubmitContact:async()=>false}),
          s.phase==='late' && text('p','expired',{className:'ev-widget-status',role:'status'}),
          h(E.StartChatFooter,{accent,starting:false,onAccept:()=>dispatch({type:'consent'})}))
          : h(window.React.Fragment,null,h('main',{className:'cb-body'},
            h('div',{className:'ev-reply-area'},
              s.phase==='loading' && h('div',{className:'ev-progress',role:'status'},h(P.LogoSpinner,{size:24})),
              s.phase==='answer' && h(P.Bubble,{author:'ai',authorName:t('header'),text:t('firstAnswer'),accent}),
              ['failed','unavailable'].includes(s.phase) && text('p',s.phase,{className:'ev-widget-status',role:'status'}),
              s.phase==='operator' && h(P.Bubble,{author:'operator',authorName:t('operator'),text:t('operatorAnswer'),accent}),
              s.phase==='ordinary' && h(window.React.Fragment,null,
                ...(s.sent.length?s.sent:[t('ordinaryInput')]).map((value,i)=>h(P.Bubble,{key:i,author:'client',text:value,accent})),
                h(P.Bubble,{author:'ai',authorName:t('header'),text:t('ordinaryAnswer'),accent})))),
            h(P.ChatComposer,{accent,input:s.draft,onInput:value=>dispatch({type:'draft',value}),onSend:()=>dispatch({type:'send'})})),
      h('div',{className:'cb-brand'},h('span',null,'Chatballs'))));
  }
  window.EventPanel=Panel;
})();
