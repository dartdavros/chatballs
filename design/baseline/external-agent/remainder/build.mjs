// Build static review documents only. No application or service is started.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync,writeFileSync,mkdirSync,existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname,resolve,join,relative,isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import { sha,authoredFiles,acceptedState,writePages } from './scripts/build-support.mjs';

const root=dirname(fileURLToPath(import.meta.url)),workspace=resolve(root,'../../../..');
const require=createRequire(import.meta.url);
const common=execFileSync('git',['rev-parse','--git-common-dir'],{cwd:workspace,encoding:'utf8'}).trim();
const dependencies=process.env.BASELINE_NODE_MODULES||join(dirname(resolve(workspace,common)),'node_modules');
const {build}=require(require.resolve('esbuild',{paths:[workspace,dirname(dependencies)]}));
const acceptedScreens=acceptedState(root,workspace),authored=authoredFiles(root);
const lineCounts=Object.fromEntries(authored.map(path=>[relative(root,path).replaceAll('\\','/'),readFileSync(path,'utf8').split('\n').length]));
for(const [path,count] of Object.entries(lineCounts)){assert(count<=300,`${path}: ${count} lines`);if(path.endsWith('.tsx'))assert(count<=180,`${path}: component too large`);}
const alias={'@chatballs/ui':join(workspace,'packages/ui/src/index.ts'),'@chatballs/shared':join(workspace,'packages/shared/src/index.ts'),'@chatballs/contracts':join(workspace,'packages/contracts/src/index.ts')};
mkdirSync(join(root,'generated'),{recursive:true});
const raw={name:'raw-source',setup(builder){builder.onResolve({filter:/\?raw$/},args=>({path:resolve(args.resolveDir,args.path.slice(0,-4)),namespace:'raw'}));builder.onLoad({filter:/.*/,namespace:'raw'},args=>({contents:readFileSync(args.path,'utf8'),loader:'text'}));}};
const output=await build({absWorkingDir:workspace,entryPoints:[join(root,'shared/runtime.tsx')],outfile:join(root,'generated/runtime.js'),
  bundle:true,format:'iife',minify:true,jsx:'automatic',write:false,metafile:true,nodePaths:[dependencies],alias,plugins:[raw],
  define:{'process.env.NODE_ENV':'"production"','import.meta.env':'{}'},loader:{'.svg':'dataurl','.png':'dataurl','.woff2':'dataurl'},legalComments:'none'});
let remappedMediaQueries=0;
for(const file of output.outputFiles){const text=file.path.endsWith('.css')?file.text.replace(/@media\s*(\((?:max|min)-width\s*:[^{]+)\{/g,(_,query)=>{remappedMediaQueries++;return `@container baseline ${query}{`;}):file.text;writeFileSync(file.path,text);}
const data=await build({entryPoints:[join(root,'shared/metadata.ts')],bundle:true,format:'cjs',platform:'node',write:false,nodePaths:[dependencies],alias});
const module={exports:{}};
runInNewContext(data.outputFiles[0].text,{module,exports:module.exports,URLSearchParams,location:{search:'?lang=ru'},window:{location:{search:'?lang=ru'}}});
const {cases,dictionaries}=module.exports;
assert(cases.length>=50,'Cover the full remaining design scope');assert.equal(new Set(cases.map(c=>c.id)).size,cases.length);
for(const [name,copy] of Object.entries(dictionaries)){assert.deepEqual(Object.keys(copy.ru).sort(),Object.keys(copy.en).sort(),`${name} translations`);for(const lang of ['ru','en'])for(const value of Object.values(copy[lang]))assert(typeof value==='string'&&value.trim(),`${name}.${lang}`);}
const paths=new Set(authored);
for(let path of Object.keys(output.metafile.inputs)){if(path.startsWith('<')||path.includes('node_modules'))continue;if(path.startsWith('raw:'))path=path.slice(4);path=isAbsolute(path)?path:resolve(workspace,path);if(existsSync(path))paths.add(path);}
paths.add(resolve(root,'../../platform-expansion/support.js'));
const sources=[...paths].map(path=>({path:relative(workspace,path).replaceAll('\\','/'),sha256:sha(readFileSync(path))})).sort((a,b)=>a.path.localeCompare(b.path));
const designVersion=`REST-${sha(JSON.stringify(sources)).slice(0,16)}`;
const manifest={designVersion,scope:'All remaining static design states; no runtime or integration verified',screens:cases,acceptedScreens,sources,authoredLineCounts:lineCounts,remappedMediaQueries};
writeFileSync(join(root,'generated/sources.json'),JSON.stringify(manifest,null,2)+'\n');
writeFileSync(join(root,'generated/cases.json'),JSON.stringify(cases,null,2)+'\n');
writePages(root,cases,designVersion);
console.log(JSON.stringify({designVersion,screens:cases.length,sources:sources.length,authoredMaxLines:Math.max(...Object.values(lineCounts)),acceptedScreens:acceptedScreens.map(c=>({version:c.designVersion,sources:c.sources,unchanged:true}))}));
