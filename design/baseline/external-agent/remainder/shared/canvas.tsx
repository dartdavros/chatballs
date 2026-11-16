import { useLayoutEffect } from 'react';
import { ConfigProvider } from 'antd';
import { buildTheme } from '../../../../../packages/ui/src/theme';
import { ACCENT_PRESETS, applyAppearance } from '../../../../../apps/internal-ui/src/shared/appearance';
import { cases, Screen } from './registry';
import { language, tx } from './copy';

export function RemainderCanvas() {
  const params=new URLSearchParams(location.search);
  const id=params.get('screen')??document.body.dataset.screen??'S07';
  const meta=cases.find(item=>item.id===id)??cases[0];
  const width=[320,390,1024,1440].includes(Number(params.get('width')))?Number(params.get('width')):1440;
  const height=980, dark=params.get('theme')==='dark', embed=params.get('embed')==='1';
  const accent=ACCENT_PRESETS.some(([value])=>value===params.get('accent'))?params.get('accent')!:'#0f9b8e';
  const title=language==='en'?meta.titleEn:meta.titleRu;
  useLayoutEffect(()=>{applyAppearance(dark?'DARK':'LIGHT',accent);document.title=`${meta.id} · ${title}`;},[dark,accent,title]);
  function choose(key:string,value:string){const url=new URL(location.href);url.searchParams.set(key,value);location.href=url.href;}
  function control(key:'width'|'theme'|'language'|'accent',value:string,options:string[][]){
    return <label>{tx(key)}<select aria-label={tx(key)} value={value} onChange={event=>choose(key==='language'?'lang':key,event.target.value)}>
      {options.map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label>;
  }
  return <ConfigProvider theme={buildTheme(dark,accent)}>{embed?<Screen meta={meta} width={width} height={height}/>:<div className="ea-canvas">
    <header className="ea-review"><h1>{meta.id} · {title}</h1><p>{tx('review')}</p>
      <div className="ea-review-controls">{control('width',String(width),[1440,1024,390,320].map(n=>[String(n),`${n} px`]))}
        {control('theme',dark?'dark':'light',[['light',tx('light')],['dark',tx('dark')]])}
        {control('language',language,[['ru','Русский'],['en','English']])}{control('accent',accent,ACCENT_PRESETS)}</div>
      <p>{language==='en'?meta.descriptionEn:meta.descriptionRu}</p><a href={`./review-${meta.group}.html`}>{tx('gallery')}</a>
    </header><Screen meta={meta} width={width} height={height}/>
  </div>}</ConfigProvider>;
}
