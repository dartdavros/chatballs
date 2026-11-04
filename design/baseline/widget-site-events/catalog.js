(function () {
  const { h, U, t, text } = window.EventParts;
  function Catalog({status,value,onChange,onRetry,invalid}) {
    const ready=status==='ready', loading=status==='loading', failed=status==='error';
    const options=ready?[['',t('chooseScenario')],['lunch',t('scenarioValue')],['delivery',t('scenarioOther')]]
      :[['',t(loading?'catalogLoading':'chooseScenario')]];
    return h('div',{className:'ev-catalog','data-catalog':status},
      h(U.SelectField,{label:t('scenario'),value:ready?value:'',onChange,options,disabled:!ready,invalid:failed||invalid,
        adornment:loading?h(window.SpeechProduct.LogoSpinner,{size:16}):undefined}),
      h('div',{className:'ev-catalog-help','aria-live':'polite'},
        failed?h(window.EventProduct.ServerErrors,{messages:[t('catalogError')]}):text('small',status==='empty'?'catalogEmpty':'catalogHelp'),
        h('small',null,failed?text('button','retry',{className:'link',onClick:onRetry}):
          h('a',{className:'link',href:'../service-integrations/editor.dc.html',target:'_blank',rel:'noreferrer'},t('catalog')))));
  }
  window.EventCatalog=Catalog;
})();
