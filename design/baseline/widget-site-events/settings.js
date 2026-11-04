(function () {
  const { h, U, t, text, button, icon, field, select, toggle } = window.EventParts;
  function Header() {
    return h('header', { className:'web-integration-head' },
      h('nav', { className:'portal-breadcrumbs' }, text('button','settings',{className:'link is-strong'}), h('span',null,'/'),
        text('button','integrations',{className:'link is-muted'}), h('span',null,'/'),text('b','siteName')),
      h('div',{className:'web-integration-title'},h('span',{className:'web-integration-icon'},icon('message')),text('h2','siteName'),
        text('span','working',{className:'web-integration-status'}),text('span','webAgent',{className:'web-integration-agent'})),
      h('div',{className:'web-integration-embed'},h('span',{className:'web-integration-embed-code'},text('code','snippet'),
        h(window.SpeechProduct.CopyButton,{value:t('snippet'),className:'web-integration-copy'})),text('span','embedHelp')));
  }
  function Shell({ width, id, children }) {
    const user = { role:'OWNER',fullName:t('owner'),email:'',organizationName:t('org'),organizationPublicId:'design',
      memberships:[{role:'OWNER',organizationPublicId:'design',organizationName:t('org')}] };
    const items = [['main','settings'],['fields','code'],['prechat','form'],['events','message'],['appearance','paint'],['deleteConnection','trash']]
      .map(([key,icon]) => ({key,label:t(key),icon,divider:key==='appearance',danger:key==='deleteConnection'}));
    return h('div',{className:'sp-settings-screen ev-settings',style:{width},'data-screen':id},
      h('aside',{className:'hub-sidebar'},h('div',{className:'hub-sidebar-body'},
        h(U.OrganizationSwitcher,{user,setRoute:()=>{},onSwitchOrganization:()=>{}}),
        h(U.SidebarNavigation,{user,route:'settings',setRoute:()=>{},waitingCount:0,chatScope:'all',setChatScope:()=>{},chatCounters:null}),
        h('div',{className:'profile-link'},h(U.Avatar,{user}),text('strong','owner')))),
      h(window.SpeechProduct.IntegrationPageLayout,{header:h(Header),items,activeKey:'events',note:'',onSelect:()=>{}},
        h('div',{className:'portal-settings-inner server-content server-http-content'},children)));
  }
  function Settings({ id, width }) {
    const R = window.React, [name,setName] = R.useState(id==='S03'?'':'lunch.viewed');
    const [invitation,setInvitation] = R.useState(t('invitationText')), [enabled,setEnabled] = R.useState(id==='S02');
    const [scenario,setScenario] = R.useState(id==='S01'||id==='S03'?'':'lunch');
    const [fields,setFields] = R.useState([{name:'category',type:'text',limit:'120',min:'0',max:'100',required:true}]);
    const [status,setStatus] = R.useState(id==='S04'?'loading':id==='S05'?'empty':id==='S06'?'error':'ready');
    const [submitted,setSubmitted] = R.useState(id==='S03'), [saved,setSaved] = R.useState(false);
    const invalid = !name.trim() || !invitation.trim() || !scenario || fields.some(v => !v.name.trim() || fields.filter(o=>o.name===v.name).length>1 ||
      (v.type==='text' && !(Number(v.limit)>0)) || (v.type==='number' && (!v.min || !v.max || Number(v.min)>Number(v.max))));
    const change = setter => value => { setter(value); setSaved(false); };
    return h(Shell,{width,id},
      h('div',{className:'portal-settings-heading'},text('h3','events')),
      id==='S07' && h(window.EventProduct.ServiceAlert,{tone:'error',title:t('aiDisabledTitle'),text:t('aiDisabledHelp')}),
      h('div',{className:'portal-settings-card server-form'},
        h('div',{className:'server-two-fields'},
          h('div',null,field('eventName',name,change(setName),{mono:true,error:submitted&&!name.trim()?t('requiredField'):undefined}),text('small','eventHelp')),
          h(window.EventCatalog,{status,value:scenario,onChange:change(setScenario),onRetry:()=>setStatus('ready'),invalid:submitted&&!scenario})),
        h('div',null,h(U.TextAreaField,{label:t('invitation'),value:invitation,onChange:change(setInvitation)}),text('small','invitationHelp')),
        h('div',{className:'server-enabled'},h('span',null,text('strong','enabled'),text('small','enabledHelp')),
          h(U.SwitchButton,{label:t('enabled'),checked:enabled,onClick:()=>change(setEnabled)(!enabled),className:'ui-switch'}))),
      h(window.EventSchema,{values:fields,onChange:change(setFields)}),
      submitted && invalid && h(window.EventProduct.ServerErrors,{messages:[t('invalid')]}),
      h('div',{className:'server-actions'},button('save',()=>{setSubmitted(true);setSaved(!invalid);},true,status!=='ready'),
        h('span',{className:`server-action-note${submitted&&invalid?' is-invalid':''}`,role:'status'},
          submitted&&invalid?t('fixErrors'):saved?t('saved'):'')));
  }
  window.EventSettings = Settings;
})();
