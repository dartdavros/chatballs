import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync,readdirSync,writeFileSync } from 'node:fs';
import { join,resolve } from 'node:path';
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export function authoredFiles(root){return readdirSync(root,{withFileTypes:true}).flatMap(item=>item.isDirectory()
  ? ['generated','verification'].includes(item.name)?[]:authoredFiles(join(root,item.name))
  : /\.(tsx?|m?js|css)$/.test(item.name)?[join(root,item.name)]:[]);}
export function acceptedState(root,workspace){
  return [['settings-off','S01-5037b71a01f54b2b'],['settings-unconfigured','S02-c8d1b152d7078f85'],
    ['settings-ready','S03-2122cd3c3c071bf6'],['agent-external','S04-1d495df459254c46'],
    ['agent-test','S05-6dcaa8de64ce4db2'],['agent-test-waiting','S06-26b466b218854dd8']].map(([folder,version])=>{
      const bytes=readFileSync(resolve(root,`../${folder}/generated/sources.json`)),manifest=JSON.parse(bytes);
      assert.equal(manifest.designVersion,version);
      for(const source of manifest.sources)assert.equal(sha(readFileSync(resolve(workspace,source.path))),source.sha256,source.path);
      return {folder,designVersion:version,sources:manifest.sources.length,manifestSha256:sha(bytes)};
    });
}
export const escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export function writePages(root,cases,version){
  const html=(id,title)=>`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(id+' · '+title)}</title>
<script>window.__resources={};const lang=new URLSearchParams(location.search).get('lang')==='en'?'en':'ru';localStorage.setItem('chatballs.language',lang);document.documentElement.lang=lang;</script>
<script src="./generated/runtime.js"></script><script src="../../platform-expansion/support.js"></script></head><body data-screen="${id}"><x-dc><helmet><meta name="design_doc_mode" content="canvas"><link rel="stylesheet" href="./generated/runtime.css"></helmet>{{ canvas }}</x-dc><script type="text/x-dc" data-dc-script>class Component extends DCLogic {renderVals(){return {canvas:window.React.createElement(window.RemainderCanvas)};}}</script></body></html>`;
  for(const c of cases)writeFileSync(join(root,`${c.id}.dc.html`),html(c.id,c.titleRu));
  const groups={tests:'Проверочная панель',agents:'Карточка агента',settings:'Настройки и разрешения',chat:'Чат сотрудника',client:'Клиентский виджет и согласие'};
  const style='body{margin:0;padding:24px;background:#eef0f3;color:#24272c;font:14px/1.5 system-ui,sans-serif}main{max-width:1488px;margin:auto}nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#067e74}h1{font-size:24px}h2{margin:32px 0 8px}iframe{display:block;width:1440px;height:980px;border:1px solid #d4d9dc;background:white}section{margin:32px 0 56px;overflow:auto}.note{max-width:1100px;color:#555}';
  const nav=Object.entries(groups).map(([key,title])=>`<a href="review-${key}.html">${title}</a>`).join('');
  const intro=`<p class="note">Статические макеты на общую приёмку · ${version}. Все значения и результаты — иллюстрации документа. Реальные API, ключи, сообщения, согласия и внешние действия не выполняются. Принятые S01–S06 сохранены.</p>`;
  for(const [group,title] of Object.entries(groups)){
    const entries=cases.filter(c=>c.group===group);
    const body=entries.map(c=>`<section id="${c.id}"><h2>${c.id} · ${escape(c.titleRu)}</h2><p class="note">${escape(c.descriptionRu||'Предложенное состояние на основе текущего кода. Требует личной приёмки владельца.')}</p><p><a target="_blank" href="${c.id}.dc.html?revision=${version}">Открыть отдельно и сменить язык/тему/ширину</a></p><iframe loading="lazy" title="${escape(c.titleRu)}" src="${c.id}.dc.html?embed=1&screen=${c.id}&revision=${version}"></iframe></section>`).join('');
    writeFileSync(join(root,`review-${group}.html`),`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Макеты · ${title}</title><style>${style}</style></head><body><main><h1>${title} · ${entries.length} состояний</h1>${intro}<nav>${nav}</nav>${body}</main></body></html>`);
  }
  writeFileSync(join(root,'index.html'),`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Внешнее исполнение · весь оставшийся комплект</title><style>${style}</style></head><body><main><h1>Внешнее исполнение · ${cases.length} новых состояний</h1>${intro}<nav>${nav}</nav>${cases.map(c=>`<p><a href="review-${c.group}.html#${c.id}">${c.id} · ${escape(c.titleRu)}</a></p>`).join('')}</main></body></html>`);
}
