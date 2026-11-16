// A presentation filter only. Original UI documents and their verified bundle remain unchanged.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url)),parent=resolve(root,'..');
const source=JSON.parse(readFileSync(join(parent,'generated/sources.json')));
const proofFile=['verification/revision-results.json','verification/browser-results.json'].find(path=>{
  if(!existsSync(join(parent,path)))return false;
  const candidate=JSON.parse(readFileSync(join(parent,path)));
  return candidate.status==='PASS'&&candidate.designVersion===source.designVersion;
});
assert(proofFile,'A passing browser report for the exact design version is required');
const proof=JSON.parse(readFileSync(join(parent,proofFile)));
const selectedIds=['S08','S09','S10','S11','S14','S15','S16','S17','S18','S19','S70','S71',
  'S20','S21','S22','S23','S24','S25','S26','S27','S28','S29','S30','S37','S38','S39','S72','S73',
  'S40','S41','S44','S45','S46','S47','S48','S49','S50','S60'];
const selected=selectedIds.map(id=>{const item=source.screens.find(c=>c.id===id);assert(item,id);return item;});
const excluded=source.screens.filter(c=>!selectedIds.includes(c.id));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const sourceArtifactHashes=Object.fromEntries(['generated/runtime.js','generated/runtime.css','generated/cases.json'].map(path=>[path,sha(readFileSync(join(parent,path)))]));
const selectorSha256=sha(readFileSync(fileURLToPath(import.meta.url)));
const version=`EXTERNAL-${sha(JSON.stringify({source:source.designVersion,selectedIds,sourceArtifactHashes,selectorSha256})).slice(0,16)}`;
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const groups={tests:'Проверочная панель',agents:'Внешнее исполнение в агенте',settings:'Настройки внешнего исполнения',chat:'Новая внешняя диагностика чата',client:'Согласие на внешний экспорт'};
const focus={
  tests:'На проверку — состояния внешнего запроса и разрешённые тестовые поля. Фоновая карточка не пересогласуется.',
  agents:'На проверку — блок внешнего исполнения, его доступность и отдельные предупреждения. Имя, группа, речь и остальная карточка показаны для контекста.',
  settings:'На проверку — только раздел внешнего исполнения: подключение, привязки, сроки, ключи, разрешения и последствия отключения.',
  chat:'На проверку — добавленные статусы, причины передачи и диагностика внешнего исполнения. Существующие список диалогов, карточка контакта и композер не пересогласуются.',
  client:'На проверку — только предлагаемое уточнение согласия о внешней передаче данных. Существующий виджет показан для контекста; юридическая достаточность не подтверждена.',
};
const style='body{margin:0;padding:24px;background:#eef0f3;color:#24272c;font:14px/1.5 system-ui,sans-serif}main{max-width:1488px;margin:auto}nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#067e74}h1{font-size:24px}h2{margin:32px 0 8px}iframe{display:block;width:1440px;height:980px;border:1px solid #d4d9dc;background:white}section{margin:32px 0 56px;overflow:auto}.note{max-width:1100px;color:#555}';
const nav=Object.entries(groups).map(([id,label])=>`<a href="review-${id}.html">${label}</a>`).join('');
const intro=`<p class="note">Только изменения внешнего исполнения · ${version}. Статические макеты. Общие неизменённые части приложения служат контекстом. Реальные запросы, действия и принятие согласия не выполняются.</p>`;
const url=c=>`../${c.id}.dc.html?revision=${source.designVersion}&lang=ru&theme=light&width=1440`;
for(const c of selected){
  writeFileSync(join(root,`${c.id}.html`),`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Внешнее исполнение · ${c.id} · ${esc(c.titleRu)}</title><style>${style}</style></head><body><main><h1>${c.id} · ${esc(c.titleRu)}</h1>${intro}<p class="note">${focus[c.group]}</p><p><a href="index.html">Подборка внешнего исполнения</a> · <a href="${url(c)}">Язык, тема и ширина</a></p><iframe title="${esc(c.titleRu)}" src="${url(c)}&embed=1"></iframe></main></body></html>`);
}
for(const [group,title] of Object.entries(groups)){
  const entries=selected.filter(c=>c.group===group);
  const body=entries.map(c=>`<section id="${c.id}"><h2>${c.id} · ${esc(c.titleRu)}</h2><p class="note">${focus[group]}</p><p><a target="_blank" href="${c.id}.html">Открыть отдельно</a></p><iframe loading="lazy" title="${esc(c.titleRu)}" src="${url(c)}&embed=1"></iframe></section>`).join('');
  writeFileSync(join(root,`review-${group}.html`),`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Внешнее исполнение · ${title}</title><style>${style}</style></head><body><main><h1>${title} · ${entries.length} состояний</h1>${intro}<nav>${nav}</nav>${body}</main></body></html>`);
}
const body=Object.entries(groups).map(([group,title])=>`<section><h2>${title}</h2><p class="note">${focus[group]}</p>${selected.filter(c=>c.group===group).map(c=>`<p><a href="review-${group}.html#${c.id}">${c.id} · ${esc(c.titleRu)}</a></p>`).join('')}</section>`).join('');
writeFileSync(join(root,'index.html'),`<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Внешнее исполнение · только относящиеся изменения</title><style>${style}</style></head><body><main><h1>Внешнее исполнение · только изменения этой функции</h1>${intro}<p>38 относящихся к функции кадров. 18 общих состояний исключены из предъявления.</p><nav>${nav}</nav>${body}</main></body></html>`);
const manifest={reviewVersion:version,sourceDesignVersion:source.designVersion,scope:'Only external-execution-specific UI changes; unchanged platform UI is context',verification:{path:proofFile,scope:proof.scope??'Full remaining set'},selected,excluded,sourceArtifactHashes,selectorSha256};
writeFileSync(join(root,'selection.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({reviewVersion:version,sourceDesignVersion:source.designVersion,selected:selected.length,excluded:excluded.length,uiBundleUnchanged:true}));
