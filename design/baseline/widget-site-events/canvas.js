(function () {
  const {h,U,t,text}=window.EventParts,R=window.React;
  function Canvas({section}) {
    const query=new URLSearchParams(location.search), frames=window.EventFrames.filter(f=>f.kind===section);
    const [language,setLanguage]=R.useState(query.get('lang')||'ru'),[theme,setTheme]=R.useState(query.get('theme')||'light');
    const [width,setWidth]=R.useState(Number(query.get('width'))||(section==='settings'?1440:390));
    const [selected,setSelected]=R.useState(query.get('frame')||frames[0].id),[revision,setRevision]=R.useState(0);
    window.EventLanguage=language; window.SpeechProduct.setCurrentLanguage(language);
    window.EventGo=id=>setSelected(id);
    const frame=frames.find(f=>f.id===selected)||frames[0];
    R.useLayoutEffect(()=>U.applyAppearance(theme==='dark'?'DARK':'LIGHT','#0f9b8e'),[theme]);
    const control=(key,value,change,options)=>h('label',null,t(key),h('select',{'aria-label':t(key),value,onChange:e=>change(e.target.value)},
      ...options.map(([value,label])=>h('option',{key:value,value},label))));
    const action=(key,type)=>h('button',{className:'link is-muted',onClick:()=>window.EventPreviewDispatch?.({type})},t(key));
    return h(U.ConfigProvider,{theme:{algorithm:theme==='dark'?U.theme.darkAlgorithm:U.theme.defaultAlgorithm,token:{colorPrimary:'#0f9b8e'}}},
      h('div',{className:'sp-canvas'},h('header',{className:'sp-review'},text('h1','canvasTitle'),text('p','canvasNote'),
        h('a',{className:'link is-muted',href:section==='settings'?'visitor.dc.html':'settings.dc.html'},t(section==='settings'?'visitorDocument':'settingsDocument')),
        control('frame',frame.id,setSelected,frames.map(f=>[f.id,`${f.id} · ${t(f.id)}`])),
        control('width',width,v=>setWidth(Number(v)),[320,390,768,1024,1440].map(v=>[v,String(v)])),
        control('theme',theme,setTheme,[['light',t('light')],['dark',t('dark')]]),
        control('language',language,setLanguage,[['ru','Русский'],['en','English']]),
        section==='visitor' && h('div',{className:'sp-preview-actions'},action('nextEvent','another'),action('expire','expire'),action('finish','complete'),action('takeOver','takeover'),
          h('button',{className:'link is-muted',onClick:()=>setSelected('V14')},t('reload')),
          h('button',{className:'link is-muted',onClick:()=>setRevision(revision+1)},t('reset')))),
      h('article',{className:'ev-frame'},h('div',{className:'sp-caption'},h('code',null,frame.id),text('strong',frame.id)),
        frame.note && text('p',frame.note,{className:'ev-review-note'}),
        frame.kind==='settings'?h(window.EventSettings,{key:`${frame.id}-${language}-${revision}`,id:frame.id,width})
          :h(window.EventVisitor,{key:`${frame.id}-${language}-${revision}`,frame,width}))));
  }
  window.EventCanvas=Canvas;
})();
