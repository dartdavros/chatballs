(function () {
  const {h,t,text,icon}=window.EventParts, R=window.React;
  function Visitor({frame,width}) {
    const [state,dispatch]=R.useReducer(window.EventPreviewModel.reduce,frame.phase,window.EventPreviewModel.initial);
    const launcher=R.useRef(null), invitation=R.useRef(null), animation=R.useRef(null), animate=R.useRef(false), busy=R.useRef(false);
    window.EventPreviewDispatch=dispatch;
    window.EventPreviewState=state;
    const act=type=>{
      if(busy.current)return;
      if(type==='open' && state.open && animation.current){busy.current=true;animation.current.play(false,()=>{busy.current=false;dispatch({type});launcher.current?.focus();});return;}
      if(type==='accept'||type==='open')animate.current=true;
      dispatch({type});
      if(type==='dismiss') launcher.current?.focus();
    };
    R.useEffect(()=>{
      const onKey=e=>{if(e.key==='Escape') { if(state.open) {act('open');launcher.current?.focus();} else if(state.phase==='invite') act('dismiss'); }};
      window.addEventListener('keydown',onKey);
      return ()=>window.removeEventListener('keydown',onKey);
    },[state.open,state.phase]);
    R.useEffect(()=>{
      if(!state.open)return;
      const panel=document.querySelector('.ev-panel');
      animation.current=window.EventGenie(panel,launcher.current);
      const focus=()=>panel.querySelector('button')?.focus();
      if(animate.current){busy.current=true;animation.current.play(true,()=>{busy.current=false;focus();});animate.current=false;}else focus();
      return ()=>{animation.current?.dispose();animation.current=null;};
    },[state.open]);
    return h('div',{className:'ev-site',style:{width,'--cb-accent':'#0f9b8e'},'data-screen':frame.id,'data-phase':state.phase},
      state.open && h(window.EventPanel,{state,width,dispatch:a=>a.type==='open'?act('open'):dispatch(a)}),
      state.phase==='invite' && !state.open && h('section',{ref:invitation,className:'ev-invitation','aria-label':t('invitation')},
        text('p','invitationText'),h('button',{type:'button',className:'wc-icon-button cb-composer-button ev-dismiss','aria-label':t('dismiss'),onClick:()=>act('dismiss')},icon('close')),
        h('button',{type:'button',className:'cb-start-button',onClick:()=>act('accept')},t('accept'))),
      h('button',{ref:launcher,type:'button',className:'chatballs-chat-launcher ev-launcher',style:window.EventLauncher.style,
        'aria-label':t(state.open?'close':'open'),'aria-expanded':state.open,onClick:()=>act('open'),
        dangerouslySetInnerHTML:{__html:state.open?window.EventLauncher.chevron:window.EventLauncher.bot}}));
  }
  window.EventVisitor=Visitor;
})();
