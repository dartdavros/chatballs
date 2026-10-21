// Isolated design drafts per connection. Secrets are never part of this state.
(function(){
  const fields=['responsible','source','stage','team','scenarioName','tag','enabled'];
  const pick=draft=>Object.fromEntries(fields.map(key=>[key,draft[key]]));
  const key=draft=>draft.connectionId || 'bitrix';
  const remember=draft=>({...draft.connectionScenarios,...draft.connectionName && !draft.creatingExtra?{[key(draft)]:pick(draft)}:{}});
  function select(draft,id,name){
    const scenarios=remember(draft);
    return {...draft,...pick(window.JourneyData.defaultDraft),...scenarios[id],connectionId:id,connectionName:name,connectionScenarios:scenarios,creatingExtra:false};
  }
  function begin(draft){
    return {...draft,...pick(window.JourneyData.defaultDraft),connectionScenarios:remember(draft),primaryConnection:draft.primaryConnection || draft.connectionName,
      connectionName:'',connectionId:`bitrix-${(draft.extraConnections || []).length}`,creatingExtra:true};
  }
  function update(draft,patch){
    const next={...draft,...patch};
    if(patch.connectionName!==undefined && !draft.creatingExtra){
      if(key(draft)==='bitrix')next.primaryConnection=patch.connectionName;
      else next.extraConnections=(draft.extraConnections || []).map((name,index)=>key(draft)===`bitrix-${index}`?patch.connectionName:name);
    }
    return next;
  }
  window.ConnectionDrafts={key,select,begin,update};
})();
