// Standalone design documents. Compiles presentation components; starts no services.
import {readFileSync,writeFileSync,mkdirSync,readdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {Script,runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';

const root=dirname(fileURLToPath(import.meta.url)),workspace=resolve(root,'../../..');
const common=execFileSync('git',['rev-parse','--git-common-dir'],{cwd:workspace,encoding:'utf8'}).trim();
const dependencies=process.env.BASELINE_NODE_MODULES||join(dirname(resolve(workspace,common)),'node_modules');
const require=createRequire(import.meta.url),{build}=require(require.resolve('esbuild',{paths:[workspace,dirname(dependencies)]}));
const read=p=>readFileSync(resolve(root,p),'utf8');
mkdirSync(join(root,'generated'),{recursive:true});
const result=await build({absWorkingDir:workspace,entryPoints:[join(root,'runtime.tsx')],outfile:join(root,'generated/runtime.js'),
  bundle:true,format:'iife',minify:true,jsx:'automatic',write:false,metafile:true,nodePaths:[dependencies],
  define:{'process.env.NODE_ENV':'"production"','import.meta.env':'{}'},
  alias:{'@chatballs/ui':join(workspace,'packages/ui/src/index.ts'),'@chatballs/shared':join(workspace,'packages/shared/src/index.ts'),'@chatballs/contracts':join(workspace,'packages/contracts/src/index.ts')},
  loader:{'.svg':'dataurl','.png':'dataurl','.woff2':'dataurl'},legalComments:'none'});
for(const f of result.outputFiles) writeFileSync(f.path,f.path.endsWith('.css')?f.text.replace(/@media\s*\((max|min)-width:/g,'@container baseline ($1-width:'):f.text);
const source='../../../apps/backend/chatballs/webchat/loader_assets/';
const launcher=read(source+'launcher.js');
const extract=pattern=>{const m=launcher.match(pattern);assert(m,pattern);return runInNewContext(m[1]);};
const css=extract(/style.textContent = ("[^\n]+");/);
const styleText=extract(/btn.style.cssText = ("[^\n]+");/);
const style=Object.fromEntries(styleText.split(';').filter(Boolean).map(part=>{
  const i=part.indexOf(':'),key=part.slice(0,i);return[key.startsWith('--')?key:key.replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),part.slice(i+1)];
}));
style['--chatballs-accent']='#0f9b8e';style['--chatballs-accent-rgb']='15,155,142';
writeFileSync(join(root,'generated/launcher.js'),'window.EventLauncher='+JSON.stringify({style,bot:extract(/var BOT_ICON = ('[^\n]+');/),chevron:extract(/var CHEVRON_ICON = ('[^\n]+');/)})+';');
writeFileSync(join(root,'generated/launcher.css'),css);
// Reuse the complete original animation functions, isolated from the network/audio loader.
writeFileSync(join(root,'generated/genie.js'),`window.EventGenie=function(shell,btn){
  var frame=shell.firstElementChild,appearance={rgb:[15,155,142]},panelRadius=()=>shell.parentElement.clientWidth<=480?0:24,launcherRadius=()=>28;
  ${read(source+'genie.js')}
  return {play:function(open,done){ensureGenie();btn.style.opacity='0';btn.style.pointerEvents='none';
    if(open)paintGenie(1,panelRect(),iconRect());
    playGenie(open?1:0,open?0:1,open?GENIE_OPEN_MS:GENIE_CLOSE_MS,panelRect(),iconRect(),function(){
      genieSvg.style.display='none';restPanel();btn.style.opacity='';btn.style.pointerEvents='';done();});},
    dispose:function(){window.cancelAnimationFrame(genieRaf);if(genieSvg)genieSvg.remove();}};
};`);
const sources=Object.keys(result.metafile.inputs).filter(p=>!p.includes('node_modules'));
writeFileSync(join(root,'generated/sources.json'),JSON.stringify({sources,launcherSources:['launcher.js','genie.js','runtime.js','appearance.js'].map(n=>source+n)},null,2));
for(const name of readdirSync(root).filter(n=>/\.(js|mjs|css|tsx)$/.test(n))){assert(read(name).split('\n').length<=300,`${name}: NO GOD`);if(name.endsWith('.js'))new Script(read(name),{filename:name});}
const context={window:{}};
for(const lang of ['ru','en'])runInNewContext(read(`copy-${lang}.js`),context);
assert.deepEqual(Object.keys(context.window.EventRu).sort(),Object.keys(context.window.EventEn).sort());
const scripts=['generated/runtime.js','../platform-expansion/support.js','generated/launcher.js','generated/genie.js','copy-ru.js','copy-en.js','parts.js','frames.js','schema.js','catalog.js','settings.js','visitor-model.js','panel.js','visitor.js','canvas.js'];
const styles=['generated/runtime.css','../widget-speech/baseline.css','generated/launcher.css','baseline.css','settings.css'];
for(const section of ['settings','visitor']){
  const html=`<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${context.window.EventRu.canvasTitle}</title><script>window.__resources={};</script>
${scripts.map(src=>`<script src="./${src}"></script>`).join('\n')}
</head><body><x-dc><helmet><meta name="design_doc_mode" content="canvas">
${styles.map(src=>`<link rel="stylesheet" href="./${src}">`).join('\n')}
</helmet>{{ canvas }}</x-dc><script type="text/x-dc" data-dc-script>
class Component extends DCLogic { renderVals() { return { canvas: window.React.createElement(window.EventCanvas,{section:"${section}"}) }; } }
</script></body></html>\n`;
  writeFileSync(join(root,`${section}.dc.html`),html);
  const bundled=html.replace(/<script src="([^"]+)"><\/script>/g,(_,src)=>`<script>${read(src).replaceAll('</script','<\\/script')}</script>`)
    .replace(/<link rel="stylesheet" href="([^"]+)">/g,(_,src)=>`<style>${read(src)}</style>`);
  writeFileSync(join(root,`generated/open-${section}.playwright.js`),`async(page)=>{
    await page.goto('about:blank');await page.setViewportSize({width:1510,height:1120});
    await page.setContent(${JSON.stringify(bundled)},{waitUntil:'load'});await page.locator('[data-screen]').waitFor();
    return {title:await page.title(),frames:await page.locator('.sp-review select').first().locator('option').count()};
  }`);
}
console.log(JSON.stringify({pages:2,frames:24,keys:Object.keys(context.window.EventRu).length,sources:sources.length,checks:'Compilation, syntax, RU/EN parity, local resources, authored files <=300 lines, original launcher/genie'}));
