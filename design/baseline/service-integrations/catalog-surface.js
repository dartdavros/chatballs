// One reserved catalog area for loading, failure, empty results and ready rows.
(function(){
  const {h}=window.ServiceParts,U=window.ServiceUI,t=window.jt;
  window.CatalogSurface=function CatalogSurface({state,children,onRetry}){
    if(state==='loading')return h('section',{className:'administration-card si-card si-catalog-surface si-catalog-loading',role:'status','aria-label':t('loadingServices'),'aria-busy':true},h(U.LoadingState,{variant:'inline'}));
    if(state!=='ready'){
      const title={error:'stateLoadFailed',empty:'stateEmptyCatalog','search-empty':'searchEmptyTitle'}[state];
      const help={error:'stateLoadFailedHelp',empty:'stateEmptyCatalogHelp','search-empty':'searchEmptyHelp'}[state];
      return h(U.ContentState,{className:'si-catalog-surface',icon:h(U.Icon,{name:state==='error'?'errorCircle':'search',size:22}),title:t(title),text:t(help),
        action:state==='error' && h(U.Button,{variant:'secondary',onClick:onRetry},t('reload'))});
    }
    return h('section',{className:'administration-card si-card si-catalog-surface'},h('div',{className:'si-card-body'},children));
  };
})();
