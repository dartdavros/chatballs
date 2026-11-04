async(page)=>{
  const errors=[],measurements=[],shots=[];
  const controls=page.locator('.sp-review select');
  const ids=await controls.nth(0).locator('option').evaluateAll(nodes=>nodes.map(n=>n.value));
  for(const lang of ['ru','en'])for(const theme of ['light','dark'])for(const width of [320,768,1440]){
    await controls.nth(3).selectOption(lang);await controls.nth(2).selectOption(theme);await controls.nth(1).selectOption(String(width));
    for(const id of ids){
      await controls.nth(0).selectOption(id);
      await page.locator(`[data-screen="${id}"]`).waitFor();
      const m=await page.locator('[data-screen]').evaluate(el=>{
        const box=el.getBoundingClientRect(),panel=el.querySelector('.ev-panel'),launcher=el.querySelector('.ev-launcher');
        const r=panel?.getBoundingClientRect(),l=launcher?.getBoundingClientRect();
        const overflow=[...el.querySelectorAll('input,textarea,.ev-invitation,.ev-panel,.ev-catalog,.ev-schema-scroll')]
          .filter(n=>{if(n.closest('.ev-schema-table'))return false;const b=n.getBoundingClientRect();return b.width>0&&(b.left<box.left-1||b.right>box.right+1);}).map(n=>n.className);
        return {width:box.width,scrollWidth:el.scrollWidth,overflow,panel:r?{width:r.width,height:r.height,x:r.left-box.left}:null,
          launcher:l?{width:l.width,height:l.height,right:box.right-l.right,bottom:box.bottom-l.bottom,visible:getComputedStyle(launcher).visibility}:null,
          catalog:el.querySelector('.ev-catalog')?.getBoundingClientRect().height,
          text:el.innerText,audio:el.querySelectorAll('audio').length,client:el.querySelectorAll('.cb-message--client').length};
      });
      if(m.overflow.length||m.scrollWidth>width+1)errors.push({id,lang,theme,width,reason:'overflow',m});
      if(/SPEC-|ADR-|scenario_id|organization_id|provider error|инвариант/i.test(m.text))errors.push({id,reason:'technical copy'});
      if(lang==='en'&&/[А-Яа-яЁё]/.test(m.text))errors.push({id,reason:'untranslated',text:m.text});
      if(m.audio)errors.push({id,reason:'audio element'});
      if(id==='V07'&&m.client)errors.push({id,reason:'fabricated client message'});
      if(m.launcher&&(m.launcher.width!==56||m.launcher.height!==56||Math.abs(m.launcher.right-25)>1||Math.abs(m.launcher.bottom-25)>1))errors.push({id,reason:'launcher geometry',m});
      if(width===320&&m.panel&&(Math.abs(m.panel.width-318)>1||m.launcher.visible!=='hidden'))errors.push({id,reason:'mobile panel',m});
      measurements.push({id,lang,theme,width,panel:m.panel,catalog:m.catalog});
      if((lang==='ru'&&theme==='light'&&width===1440)||(lang==='en'&&theme==='dark'&&width===320)){
        const path=`design/baseline/widget-site-events/verification/${id}-${lang}-${theme}-${width}.png`;
        await page.locator('[data-screen]').screenshot({path});shots.push(path);
        if(id.startsWith('S')){
          await page.locator('.portal-settings-content').evaluate(el=>{el.scrollTop=el.scrollHeight;});
          const end=`design/baseline/widget-site-events/verification/${id}-${lang}-${theme}-${width}-bottom.png`;
          await page.locator('[data-screen]').screenshot({path:end});shots.push(end);
        }
      }
    }
  }
  for(const width of [320,768,1440]){
    const sizes=measurements.filter(m=>m.width===width&&['S02','S04','S05','S06'].includes(m.id)).map(m=>m.catalog);
    if(new Set(sizes).size>1)errors.push({reason:'catalog shifts between states',width,sizes});
    const panels=measurements.filter(m=>m.width===width&&['V06','V07','V08','V09'].includes(m.id)).map(m=>JSON.stringify(m.panel));
    if(new Set(panels).size>1)errors.push({reason:'panel shifts between states',width});
  }
  return {checked:measurements.length,measurements,shots,errors};
}
