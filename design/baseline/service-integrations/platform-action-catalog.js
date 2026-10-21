// Design examples by public product area, not an implementation of a domain-action registry.
(function () {
  const rows = [
    ['dialogs','dialogsGroup',[['close','closeDialog','paramDialog','text'],['transfer','transferDialog','paramGroup','text']]],
    ['messages','messagesGroup',[['send','sendMessage','paramMessage','text'],['deleteMessage','deleteMessage','paramMessageId','text']]],
    ['contacts','contactsGroup',[['findContact','findContact','paramSearch','text'],['updateContact','updateContact','paramContact','text']]],
    ['tags','tagsGroup',[]],['people','peopleGroup',[]],
    ['agents','agentsGroup',[['chooseAgent','chooseAgent','paramAgent','text']]],
    ['skills','skillsGroup',[['enableSkill','enableSkill','paramSkill','text']]],
    ['knowledge','knowledgeGroup',[['findKnowledge','findKnowledge','paramSearch','text']]],
    ['portals','portalsGroup',[['publishArticle','publishArticle','paramArticle','text']]],
    ['files','filesGroup',[['attachFile','attachFile','paramFile','file']]],
    ['calls','callsGroup',[['startCall','startCall','paramDialog','text']]],
    ['notifications','notificationsGroup',[['notification','notificationAction','paramMessage','text']]],
    ['reports','reportsGroup',[['report','createReport','paramReport','text']]],
    ['settings','settingsGroup',[['organizationName','changeOrganizationName','paramOrganizationName','text']]],
    ['administration','administrationGroup',[['invite','inviteEmployee','paramEmail','text']]],
  ];
  const original = window.CustomModel.operations.chatballs;
  window.PlatformActions = { rows, groupOf: operation => operation === 'tag' ? 'tags' : ['assign','notify'].includes(operation) ? 'people' : operation === 'link' ? 'contacts' : rows.find(row=>row[2].some(op=>op[0]===operation))?.[0] || 'dialogs' };
  window.CustomModel.operations.chatballs = [...original,...rows.flatMap(row=>row[2])];
})();
