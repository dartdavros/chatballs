// Native file inspection of the complete remaining design set. No backend or server.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {acceptedState,sha} from './scripts/build-support.mjs';
import {measure} from './scripts/measure.mjs';
import {validate} from './scripts/assert-screen.mjs';
const root=dirname(fileURLToPath(import.meta.url)),workspace=resolve(root,'../../../..');
const common=execFileSync('git',['rev-parse','--git-common-dir'],{cwd:workspace,encoding:'utf8'}).trim();
const deps=process.env.BASELINE_NODE_MODULES||join(dirname(resolve(workspace,common)),'node_modules');
const require=createRequire(import.meta.url),{chromium}=require(require.resolve('@playwright/test',{paths:[workspace,dirname(deps)]}));
const manifest=JSON.parse(readFileSync(join(root,'generated/sources.json'))),cases=manifest.screens;
const output=join(root,'verification');mkdirSync(output,{recursive:true});
const results=[],failures=[],errors=[],network=[],screenshots=[],transientAttempts=[];
const accepted=acceptedState(root,workspace);
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage();page.setDefaultTimeout(30000);
// Painting the large shared bundle may take longer than a DOM assertion on a cold browser.
const capture=path=>page.screenshot({path,timeout:45000});
let current='',status='RUNNING';
page.on('pageerror',error=>errors.push({screen:current,message:error.message}));
page.on('console',message=>{if(message.type()==='error')errors.push({screen:current,message:message.text()});});
page.on('request',request=>{if(/^https?:/.test(request.url()))network.push({screen:current,url:request.url()});});
async function inspectOnce(c,test,captureImages=false){
  current=c.id;
  await page.setViewportSize({width:test.width,height:980});
  const url=new URL(`${c.id}.dc.html`,import.meta.url);
  url.search=new URLSearchParams({screen:c.id,embed:'1',lang:test.lang,theme:test.theme,width:String(test.width),accent:test.accent??'#0f9b8e'});
  try{
    await page.goto(url.href,{waitUntil:'load'});await page.locator('.ea-screen').waitFor();await page.evaluate(()=>document.fonts.ready);
    if(c.group==='client')await page.waitForFunction(()=>Boolean(document.querySelector('[data-client-widget-host]')?.shadowRoot?.querySelector('[data-consent-state]')));
    if(c.modal){
      await page.locator('.ant-modal').waitFor({state:'visible'});
      await page.evaluate(async()=>{
        const animations=document.getAnimations().filter(animation=>animation.effect?.target instanceof Element
          && animation.effect.target.closest('.ant-modal-root') && animation.effect.getTiming().iterations!==Infinity);
        await Promise.all(animations.map(animation=>animation.finished.catch(()=>{})));
      });
      await page.waitForFunction(()=>{const element=document.querySelector('.ant-modal');if(!element)return false;
        const style=getComputedStyle(element),matrix=new DOMMatrix(style.transform==='none'?undefined:style.transform);
        return Number(style.opacity)===1&&Math.abs(matrix.a-1)<.001&&Math.abs(matrix.d-1)<.001;});
    }
    const geometry=await page.evaluate(measure);validate(geometry,c,test);results.push({id:c.id,...test,geometry});
    if(captureImages){
      const name=`${c.id}-${test.lang}-${test.theme}-${test.width}.png`;
      await capture(join(output,name));screenshots.push(name);
      if(c.group==='settings'&&['S20','S21','S22','S23','S33','S34','S35','S38','S39','S72','S73'].includes(c.id)){
        for(const [marker,part] of [['[data-agent-bindings]','bindings'],['[data-processing-settings]','processing'],['[data-data-policy]','data'],['[data-template-grants]','templates']]){
          const section=page.locator(marker);if(await section.count()){await section.scrollIntoViewIfNeeded();const focused=name.replace('.png',`-${part}.png`);await capture(join(output,focused));screenshots.push(focused);}
        }
      }
      await page.evaluate(()=>{for(const n of document.querySelectorAll('.settings-content,.hub-scroll,.sales-timeline,.agent-test-feed'))n.scrollTop=n.scrollHeight;});
      const bottom=name.replace('.png','-bottom.png');await capture(join(output,bottom));screenshots.push(bottom);
    }
    return true;
  }catch(error){failures.push({id:c.id,...test,error:error.message});const name=`FAIL-${c.id}-${test.lang}-${test.theme}-${test.width}.png`;await page.screenshot({path:join(output,name),timeout:45000}).catch(()=>{});return false;}
}
async function inspect(c,test,captureImages=false){
  const checkpoint=failures.length;
  if(await inspectOnce(c,test,captureImages))return;
  const failure=failures[checkpoint];
  // One readiness/transport retry; actual layout assertions are never retried or removed.
  if(/Timeout \d+ms exceeded|TimeoutError/.test(failure.error)){
    transientAttempts.push({...failure,attempt:1});failures.splice(checkpoint,1);
    await inspectOnce(c,test,captureImages);
  }
}
try{
  for(const c of cases)await inspect(c,{lang:'ru',theme:'light',width:1440},true);
  console.log(JSON.stringify({phase:'all-desktop',cases:cases.length,failures:failures.length,errors:errors.length}));
  assert.deepEqual(failures,[],'Desktop design checks');assert.deepEqual(errors,[],'Browser render errors');assert.deepEqual(network,[],'Static documents cannot request HTTP(S)');
  let count=0;
  for(const lang of ['ru','en'])for(const theme of ['light','dark'])for(const width of [1440,1024,390,320]){
    if(lang==='ru'&&theme==='light'&&width===1440)continue;
    for(const c of cases){await inspect(c,{lang,theme,width},lang==='en'&&theme==='dark'&&width===1440);if(++count%80===0)console.log(JSON.stringify({phase:'matrix',completed:count,total:cases.length*15,failures:failures.length}));}
  }
  for(const group of ['tests','agents','settings','chat','client']){
    const c=cases.find(item=>item.group===group);
    for(const accent of ['#1677ff','#e8590c'])await inspect(c,{lang:'ru',theme:'light',width:1440,accent});
    await inspect(c,{lang:'ru',theme:'light',width:1440});await page.evaluate(()=>{document.body.style.zoom='2';});
    const zoom=await page.evaluate(measure);assert.equal(zoom.width,2880);assert.deepEqual(zoom.overflow,[]);results.push({id:c.id,check:'200% CSS scale',geometry:zoom});
  }
  assert.deepEqual(failures,[]);assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  const changed=manifest.sources.filter(source=>sha(readFileSync(resolve(workspace,source.path)))!==source.sha256).map(source=>source.path);
  assert.deepEqual(changed,[],'Rebuild after any source change');acceptedState(root,workspace);
  status='PASS';console.log(JSON.stringify({status,designVersion:manifest.designVersion,cases:cases.length,matrix:cases.length*16,additionalAccents:10,zoomCases:5,errors:errors.length,network:network.length,screenshots:screenshots.length,retriedTimeouts:transientAttempts.length}));
}catch(error){status='FAIL';console.log(JSON.stringify({status,error:error.message,failures,errors,network}));process.exitCode=1;}
finally{writeFileSync(join(output,'browser-results.json'),JSON.stringify({status,designVersion:manifest.designVersion,accepted,results,failures,transientAttempts,errors,network,screenshots},null,2)+'\n');await browser.close();}
