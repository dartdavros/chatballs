// Executed inside the inspected static document only.
export function measure(){
  const frame=document.querySelector('.ea-screen'), rect=frame.getBoundingClientRect();
  const shell=frame.querySelector('.hub-shell'), boundary=shell?.getBoundingClientRect()??rect;
  const panel=frame.querySelector('.agent-test-panel');
  const selectors='.agent-card,.agent-head,.agent-grid,.agent-column,.agent-test-panel,.agent-test-head,.agent-action-test-mode,.agent-test-data,.agent-test-feed,.agent-test-composer,.administration-card,.settings-content-inner,.service-connect-fields,.sales-conversation,.sales-timeline-inner,.sales-dialog-head,.sales-context';
  const overflow=[];
  for(const node of frame.querySelectorAll(selectors)){
    const style=getComputedStyle(node),r=node.getBoundingClientRect();
    if(style.display==='none'||style.visibility==='hidden'||!r.width||!r.height)continue;
    const limit=node.closest('.agent-test-panel')?.getBoundingClientRect()??boundary;
    if(node.scrollWidth>node.clientWidth+2 && !/auto|scroll|hidden|clip/.test(style.overflowX))overflow.push({className:node.className,client:node.clientWidth,scroll:node.scrollWidth});
    if(r.left<limit.left-2||r.right>limit.right+2)overflow.push({className:node.className,left:r.left-limit.left,right:r.right-limit.right});
  }
  const shadow=frame.querySelector('[data-client-widget-host]')?.shadowRoot;
  const modal=[...document.querySelectorAll('.ant-modal')].find(node=>getComputedStyle(node).display!=='none'&&node.getBoundingClientRect().height);
  const modalRect=modal?.getBoundingClientRect();
  const buttons=[...frame.querySelectorAll('button')];
  return {id:frame.dataset.screen,width:Math.round(rect.width),height:Math.round(rect.height),client:frame.clientWidth,scroll:frame.scrollWidth,
    lang:document.documentElement.lang,theme:document.documentElement.dataset.theme,overflow,
    minWidth:shell?getComputedStyle(shell).minWidth:null,shellWidth:Math.round(boundary.width),
    panel:panel?{width:Math.round(panel.getBoundingClientRect().width),height:Math.round(panel.getBoundingClientRect().height),inputs:[...panel.querySelectorAll('input')].map(n=>({value:n.value,disabled:n.disabled})),reply:panel.querySelectorAll('.agent-test-reply').length,error:panel.querySelectorAll('.agent-test-error').length}:null,
    execution:frame.querySelector('[data-execution-mode]')?.getAttribute('data-execution-mode'),
    blocker:frame.querySelectorAll('.agent-blocker').length,testDisabled:frame.querySelector('.agent-test-button')?.disabled,
    startDisabled:frame.querySelector('.agent-toggle')?.disabled,waiting:frame.querySelectorAll('[data-external-waiting] .logo-spinner').length,
    passwords:[...frame.querySelectorAll('input[type=password]')].map(n=>n.value),
    serviceLast:[...frame.querySelectorAll('.settings-subnav-group')].find(n=>n.getAttribute('aria-labelledby')==='settings-group-service')?.querySelector('button.settings-subnav-item:last-child')?.getAttribute('data-settings-item'),
    modal:modalRect?{left:modalRect.left,right:modalRect.right,width:modalRect.width}:null,
    clientShadow:shadow?{consent:shadow.querySelector('[data-consent-state]')?.getAttribute('data-consent-state'),inputs:shadow.querySelectorAll('input,textarea').length,
      text:shadow.textContent.replaceAll(/<[^>]+>/g,'').slice(-8000),overflow:shadow.host.scrollWidth>shadow.host.clientWidth+2}:null,
    unknown:frame.querySelectorAll('[data-delivery=unknown]').length,htmlFallback:frame.querySelectorAll('[data-channel-fallback]').length,
    feature:frame.querySelector('[data-external-feature]')?.getAttribute('data-external-feature'),
    enableError:frame.querySelectorAll('[data-feature-enable-error]').length,
    connectionActive:frame.querySelector('[data-connection-active]')?.getAttribute('data-connection-active'),
    policyTargets:frame.querySelectorAll('[data-policy-agent="support"][data-policy-connection="support-service"]').length,
    emptyCatalog:frame.querySelectorAll('[data-template-catalog="empty"]').length,
    initiativeTargets:frame.querySelectorAll('[data-initiative-agent="support"][data-initiative-connection="support-service"]').length,
    buttonText:buttons.map(n=>n.textContent.trim()).filter(Boolean),
  };
}
