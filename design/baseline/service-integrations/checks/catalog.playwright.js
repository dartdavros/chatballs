// The same catalog area remains reserved in every data state.
async page => {
  const errors=[],measurements=[],requests=[],capture=r=>{if(/^https?:/.test(r.url()))requests.push(r.url());};
  page.on('request',capture);
  const frames=page.locator('.si-review select').first(),content=page.locator('.settings-content');
  for(const width of [1440,1024])for(const theme of ['light','dark']){
    await page.setViewportSize({width,height:1100});
    await page.locator('.si-review select').nth(1).selectOption(String(width));
    await page.locator('.si-review select').nth(2).selectOption(theme);
    const rects=[];
    for(const id of ['J01','Y02','Y03','Y16']){
      await frames.selectOption(id);
      const rect=await content.locator('.si-catalog-surface').evaluate(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height};});
      rects.push(rect);measurements.push({id,width,theme,...rect});
      if(id==='Y16' && await content.locator('.loading-state').count()!==1)errors.push({id,width,theme,error:'Shared loading state missing'});
    }
    if(rects.some(r=>JSON.stringify(r)!==JSON.stringify(rects[0])))errors.push({width,theme,error:'Catalog changed geometry',rects});
    await frames.selectOption('J01');await content.getByPlaceholder('Найти сервис').fill('missing-adapter');
    const empty=await content.locator('.si-catalog-surface').boundingBox();
    if(JSON.stringify(empty)!==JSON.stringify(rects[0]))errors.push({width,theme,error:'Search empty changed geometry',empty});
    await frames.selectOption('Y03');await content.getByRole('button',{name:'Повторить загрузку',exact:true}).click();
    if(await frames.inputValue()!=='J01')errors.push('Catalog retry did not return to ready');
  }
  page.off('request',capture);return{errors,requests,measuredScreens:measurements.length,verified:'reserved catalog geometry across ready, empty, failed, loading and search-empty; shared spinner; retry'};
}
