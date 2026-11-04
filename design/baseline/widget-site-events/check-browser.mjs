// Repeatable native file:// browser checks in an isolated Chrome profile. No server.
import {createRequire} from 'node:module';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Script} from 'node:vm';
import assert from 'node:assert/strict';
const root=dirname(fileURLToPath(import.meta.url)),workspace=resolve(root,'../../..');
const common=execFileSync('git',['rev-parse','--git-common-dir'],{cwd:workspace,encoding:'utf8'}).trim();
const dependencies=process.env.BASELINE_NODE_MODULES||join(dirname(resolve(workspace,common)),'node_modules');
const require=createRequire(import.meta.url),{chromium}=require(require.resolve('@playwright/test',{paths:[workspace,dirname(dependencies)]}));
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[],failures=[],network=[];
const sections=process.argv[2]?[process.argv[2]]:['settings','visitor'];
assert(sections.every(section=>['settings','visitor'].includes(section)),'Use settings or visitor');
mkdirSync(join(root,'verification'),{recursive:true});
try{
  const page=await browser.newPage({viewport:{width:1510,height:1120}});page.setDefaultTimeout(10000);
  page.on('pageerror',e=>failures.push(e.message));page.on('console',m=>{if(m.type()==='error')failures.push(m.text());});
  page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  for(const section of sections){
    await page.goto(new URL(`${section}.dc.html`,import.meta.url).href);await page.locator('[data-screen]').waitFor();
    for(const name of section==='settings'?['matrix','interactions','schema']:['matrix','interactions']){
      const check=new Script(`(${readFileSync(join(root,`checks/${name}.playwright.js`),'utf8')})`).runInNewContext();
      const result=await check(page);results.push({section,name,...result});console.log(JSON.stringify({section,name,checked:result.checked,errors:result.errors}));
      assert.equal(result.errors.length,0,JSON.stringify(result.errors));
    }
    await page.reload();await page.locator('[data-screen]').waitFor();
  }
  assert.equal(failures.length,0,JSON.stringify(failures));assert.equal(network.length,0,JSON.stringify(network));
  console.log('PASS: native file documents, browser interactions, geometry, keyboard, zoom, no HTTP or errors.');
}finally{
  writeFileSync(join(root,`verification/browser${process.argv[2]?'-'+process.argv[2]:''}-results.json`),JSON.stringify({results,failures,network},null,2));
  await browser.close();
}
