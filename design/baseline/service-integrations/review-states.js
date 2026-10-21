// Required design states, selected outside the product frame in the review toolbar.
(function () {
  const { h, text, card, line, actions, frame, note } = window.ServiceParts, U = window.ServiceUI, W = window.Workbench, t = window.jt;
  function State({ title, help, target = 'J10', label = 'backToConnection', icon = 'errorCircle' }) {
    const c = window.Custom.use();
    return h(U.ContentState, { icon: h(U.Icon, { name: icon, size: 22 }), title: t(title), text: t(help),
      action: h(W.Button, { label, onClick: () => c.go(target) }) });
  }
  function Concurrent() {
    const c = window.Custom.use();
    return h('div', { className: 'si-card-body' }, note(t('stateConcurrent'),t('stateConcurrentHelp'),'warn'),
      card(t('scenario'),line(t('yourVersion'),t('yourVersionText')),line(t('savedVersion'),t('savedVersionText'))),
      actions(h(W.Button,{label:'saveCopy',primary:true,onClick:c.copy}),h(W.Button,{label:'openSaved',onClick:()=>{c.restore();c.go('X01');}})));
  }
  function SaveError() {
    const c = window.Custom.use();
    return h('div',{className:'si-card-body'},note(t('stateSaveError'),t('stateSaveErrorHelp'),'error'),
      card(c.plan.name || t('customTitle'),h(window.CustomSteps.Summary,{steps:c.plan.steps})),
      actions(h(W.Button,{label:'retrySave',primary:true,onClick:c.save}),h(W.Button,{label:'customBack',onClick:()=>c.go('X01')})));
  }
  function Manage({ blocked = false }) {
    const c = window.Custom.use(), [confirm, show] = window.React.useState('');
    return h('div',{className:'si-card-body'},
      blocked ? note(t('stateDeleteBlocked'),t('stateDeleteBlockedHelp'),'warn') : card(t('noScenario'),text('p',t('noScenarioHelp')),
        actions(h(W.Button,{label:'choosePreset',onClick:()=>c.go('J03')}),h(W.Button,{label:'ownScenario',onClick:()=>c.open('J03')}))),
      actions(h(W.Button,{label:'disableConnection',onClick:()=>show('disable')}),h(W.Button,{label:'removeConnection',danger:true,disabled:blocked,onClick:()=>show('delete')})),
      !!confirm && h(window.CanvasDialog,{open:true,onClose:()=>show(''),tone:confirm==='delete'?'danger':'warning',icon:'errorCircle',title:t(confirm==='delete'?'confirmDelete':'confirmDisable'),description:t(confirm==='delete'?'deleteHelp':'disableHelp'),
        actions:actions(h(W.Button,{label:confirm==='delete'?'removeConnection':'disableConnection',danger:confirm==='delete',primary:confirm!=='delete',onClick:()=>c.go(confirm==='delete'?'Y01':'Y06')}),h(W.Button,{label:'cancel',onClick:()=>show('')}))}));
  }
  window.ReviewStates = function () {
    const state = (id, title, help, options = {}) => frame(id,t(title),t('integrations'),'',[h(State,{title,help,...options})],{root:true});
    const screen = (id,title,component) => frame(id,t(title),t(title),'',[component],{root:true});
    const catalog=(id,title,state)=>frame(id,t(title),t('catalogTitle'),t('catalogLead'),[h(window.JourneyConnect.Catalog,{state})],{backFrame:'J10',backLabel:t('services')});
    return [
      state('Y01','stateEmptyConnections','stateEmptyConnectionsHelp',{target:'J01',label:'addService',icon:'plug'}),
      catalog('Y02','stateEmptyCatalog','empty'),catalog('Y03','stateLoadFailed','error'),
      state('Y04','stateForbidden','stateForbiddenHelp'),state('Y05','stateRevoked','stateRevokedHelp'),
      state('Y06','stateDisabled','stateDisabledHelp',{target:'J03',label:'enableConnection'}),state('Y07','stateUnavailable','stateUnavailableHelp',{target:'J11',label:'retry'}),
      state('Y08','stateIncompatible','stateIncompatibleHelp',{target:'X01',label:'editScenario'}),
      screen('Y09','stateConcurrent',h(Concurrent)), screen('Y10','stateSaveError',h(SaveError)),
      screen('Y11','stateDeleteBlocked',h(Manage,{blocked:true})),screen('Y12','noScenario',h(Manage)),
      state('Y13','stateMissingDirectory','stateMissingDirectoryHelp',{target:'J04',label:'reload'}),state('Y14','stateMissingFile','stateMissingFileHelp',{target:'X03',label:'change'}),
      frame('Y15',t('storageTitle'),t('storageTitle'),t('storageLead'),[h(window.RetentionSettings)],{root:true,section:'Организация'}),
      catalog('Y16','loadingServices','loading'),
    ];
  };
})();
