// Repeats the task-local Playwright checks against the actual static baseline.
// No web server, API responses, project fixtures or account changes are created.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import assert from 'node:assert/strict';

const root=dirname(fileURLToPath(import.meta.url)),workspace=resolve(root,'../../..');
const common=execFileSync('git',['rev-parse','--git-common-dir'],{cwd:workspace,encoding:'utf8'}).trim();
const dependencyRoot=process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace,common)),'node_modules');
const require=createRequire(import.meta.url),{chromium}=require(require.resolve('@playwright/test',{paths:[workspace,dirname(dependencyRoot)]}));
const names=['journey','vendors','custom','editor-ui','workbench','values','parameters','catalog','layout'];
const selected=process.argv.slice(2).length?process.argv.slice(2):names;
assert(selected.every(name=>names.includes(name)),'Unknown baseline check');
const load=name=>new Script(`(${readFileSync(join(root,name),'utf8')})`,{filename:name}).runInNewContext();
const open=load('generated/open.playwright.js');
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
  const page=await browser.newPage();page.setDefaultTimeout(10000);
  const pageErrors=[],consoleErrors=[];page.on('pageerror',error=>pageErrors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text());});
  for(const name of selected){
    if(name!=='editor-ui'||!selected.includes('custom')){
      await open(page);
      if(name==='editor-ui')assert.equal((await load('checks/custom.playwright.js')(page)).errors.length,0);
    }
    const result=await load(`checks/${name}.playwright.js`)(page);
    assert.equal(result.errors.length,0,JSON.stringify({name,errors:result.errors}));
    assert.equal((result.requests || result.apiRequests || []).length,0,`${name}: baseline contacted an API`);
    assert.equal(pageErrors.length,0,JSON.stringify(pageErrors));
    assert.equal(consoleErrors.length,0,JSON.stringify(consoleErrors));
    console.log(JSON.stringify({check:name,status:'passed',screens:result.count || result.measuredScreens,verified:result.verified}));
  }
  for(const name of ['journey','connections','editor','settings']){
    await page.goto(new URL(`${name}.dc.html`,import.meta.url).href);
    await page.locator('.si-screen').waitFor();
    await page.waitForFunction(()=>[...document.images].every(image=>image.complete && image.naturalWidth>0));
    assert.equal(await page.locator('.si-review select').first().locator('option').count(),66);
    assert.equal(pageErrors.length,0,JSON.stringify(pageErrors));
    assert.equal(consoleErrors.length,0,JSON.stringify(consoleErrors));
  }
  console.log(JSON.stringify({check:'standalone',status:'passed',entries:4,verified:'native file URLs, local dependencies and logos, no console or page errors'}));
}finally{await browser.close();}
