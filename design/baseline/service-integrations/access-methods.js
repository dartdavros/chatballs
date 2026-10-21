(function () {
  const { h, card, actions, note, frame } = window.ServiceParts, W = window.Workbench, t = window.jt;
  const methods = [['key','authKey'],['bearer','authBearer'],['basic','authBasic'],['signature','authSignature'],['certificate','authCertificate'],['custom','authCustom']];
  function Access({ method: initial = 'key' }) {
    const [method, choose] = window.React.useState(initial), [values, set] = window.React.useState({}), [submitted, submit] = window.React.useState(false), [saved, save] = window.React.useState(false);
    const fields = { key: ['authSecret'], bearer: ['authSecret'], basic: ['authLogin','authPassword'], signature: ['authPublicKey','authSecret'], certificate: ['authCertificateFile','authPrivateKey'], custom: ['authProject','authSecret'] }[method];
    const update = (key,value) => set(old => ({ ...old, [key]: value }));
    const valid = fields.every(key => !!values[key]?.trim());
    const control = key => ['authCertificateFile','authPrivateKey'].includes(key) ? h('label',{className:'readonly-field si-file-field',key},h('span',null,t(key)),
      h('input',{type:'file','aria-label':t(key),accept:key==='authCertificateFile'?'.pem,.crt,.cer':'.pem,.key',onChange:event=>update(key,event.target.files[0]?.name || '')}))
      : h(W.Field,{key,label:key,value:values[key] || '',type:['authSecret','authPassword'].includes(key)?'password':'text',onChange:value=>update(key,value)});
    return h('div',{className:'si-card-body'},card(t('authTitle'),h(W.Select,{label:'accessMethod',value:method,options:methods,onChange:value=>{choose(value);set({});submit(false);save(false);}}),
      h(W.Help,{label:'authHelp'}), saved ? note(t('authSaved'),t('authSavedHelp'),'ok') : fields.map(control),
      method==='certificate' && !saved && h(W.Field,{label:'authCertificatePassword',value:values.pass || '',type:'password',onChange:value=>update('pass',value)}),
      submitted && !valid && !saved && note('',t('authSecretError'),'error')),
      h(W.Help,{label:'authSafeCheck'}),actions(saved ? h(W.Button,{label:'replaceAccess',onClick:()=>{save(false);submit(false);}})
        : h(W.Button,{label:'saveUnchecked',primary:true,onClick:()=>{submit(true);if(valid){set({});save(true);}}})));
  }
  window.AccessMethodFrames = () => methods.map(([method],index) => frame(`Z0${index+1}`,t(methods[index][1]),t('authTitle'),t('authLead'),[h(Access,{method})],{root:true}));
})();
