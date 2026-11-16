import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url)),parent=resolve(root,'..');
const require=createRequire(import.meta.url),{chromium}=require(require.resolve('@playwright/test',{paths:[resolve(root,'../../../../..')]}));
const data=JSON.parse(readFileSync(join(root,'selection.json'))),proof=JSON.parse(readFileSync(join(parent,data.verification?.path??'verification/browser-results.json')));
assert.equal(proof.status,'PASS');assert.equal(proof.designVersion,data.sourceDesignVersion);assert.equal(data.selected.length,38);assert.equal(data.excluded.length,18);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
for(const [path,hash] of Object.entries(data.sourceArtifactHashes))assert.equal(sha(readFileSync(join(parent,path))),hash);
assert.equal(sha(readFileSync(join(root,'build-review.mjs'))),data.selectorSha256);
const pages=['index.html',...['tests','agents','settings','chat','client'].map(group=>`review-${group}.html`),...data.selected.map(c=>`${c.id}.html`)];
let links=0;
for(const page of pages){
  const html=readFileSync(join(root,page),'utf8');
  for(const match of html.matchAll(/(?:href|src)="([^"]+)"/g)){
    const target=match[1].split(/[?#]/)[0];assert(!/^https?:/.test(target));assert(existsSync(resolve(root,target)),target);links++;
  }
}
const errors=[],network=[],frames=[];
const browser=await chromium.launch({channel:'chrome',headless:true});
let status='RUNNING';
try{
  const page=await browser.newPage({viewport:{width:1510,height:1180}});page.setDefaultTimeout(30000);
  page.on('pageerror',error=>errors.push(error.message));page.on('request',req=>{if(/^https?:/.test(req.url()))network.push(req.url());});
  await page.goto(new URL('index.html',import.meta.url).href);
  const index=await page.locator('body').innerText();
  for(const c of data.selected)assert(index.includes(c.id+' ·'));
  for(const c of data.excluded)assert(!index.includes(c.id+' ·'),`Generic state exposed: ${c.id}`);
  for(const c of data.selected){
    await page.goto(new URL(`${c.id}.html`,import.meta.url).href);
    const frame=page.frameLocator('iframe');await frame.locator(`.ea-screen[data-screen="${c.id}"]`).waitFor();
    assert.equal(await page.locator('iframe').count(),1);frames.push(c.id);
  }
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);status='PASS';
  console.log(JSON.stringify({status,reviewVersion:data.reviewVersion,selected:frames.length,excluded:data.excluded.length,links,browserErrors:0,httpRequests:0,uiBundleUnchanged:true}));
}finally{writeFileSync(join(root,'verification.json'),JSON.stringify({status,reviewVersion:data.reviewVersion,sourceDesignVersion:data.sourceDesignVersion,frames,excluded:data.excluded.map(c=>c.id),links,errors,network,uiBundleUnchanged:true},null,2)+'\n');await browser.close();}
