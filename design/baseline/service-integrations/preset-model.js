// Editable organization copies use the same tree as a scenario created from scratch.
(function () {
  function create(service,draft) {
    const M=window.CustomModel,t=window.jt,plan=M.blank(),first=M.makeStep('action');
    first.service=service; first.operation={bitrix:'lead',amo:'deal',mindbox:'customer'}[service];
    first.connection=service==='bitrix'?window.ConnectionDrafts.key(draft):service;
    first.source='context'; first.value=t('contextTitle');
    plan.group=(service==='bitrix'?draft.team:draft.vendors?.[service]?.team)===t('sales')?'sales':'support';
    plan.name=service==='bitrix'?draft.scenarioName:t(service==='amo'?'amoPreset':'mindboxPreset');
    plan.condition='contact';plan.conditions={id:'preset-conditions',mode:'all',rules:[{id:'preset-contact',field:'contact',value:''}]};
    // Directly selected enabled frames use the same illustrated employee as J06.
    first.params=service==='bitrix'?{owner:draft.responsible || t('memberAnna'),stage:draft.stage,source:draft.source}:service==='amo'?{owner:draft.vendors?.amo?.owner || t('memberAnna'),pipeline:draft.vendors?.amo?.pipeline || t('pipelineSales'),stage:draft.vendors?.amo?.stage || t('stageNew')}:{};
    plan.steps=[first];
    if(service!=='mindbox'){
      const linked=M.makeStep('action');linked.service='chatballs';linked.operation='link';linked.source='step';linked.value=first.id;plan.steps.push(linked);
    }
    return plan;
  }
  window.PresetModel={create};
})();
