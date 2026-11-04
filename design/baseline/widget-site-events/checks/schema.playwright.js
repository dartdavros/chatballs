async(page)=>{
  const errors=[],measurements=[],controls=page.locator('.sp-review select');let checked=0;
  const check=(ok,name)=>{checked++;if(!ok)errors.push(name);};
  for(const lang of ['ru','en'])for(const theme of ['light','dark'])for(const width of [320,768,1440]){
    await controls.nth(3).selectOption(lang);await controls.nth(2).selectOption(theme);await controls.nth(1).selectOption(String(width));
    await controls.nth(0).selectOption('S01');await controls.nth(0).selectOption('S02');
    const row=page.locator('.ev-schema-row'), typeLabel=lang==='ru'?'Тип':'Type';
    for(const [type,label] of [['text',lang==='ru'?'Текст':'Text'],['number',lang==='ru'?'Число':'Number'],['boolean',lang==='ru'?'Да / нет':'Yes / no']]){
      await row.getByRole('button',{name:typeLabel,exact:true}).click();
      await page.getByRole('button',{name:label,exact:true}).click();
      await page.getByRole('button',{name:label,exact:true}).waitFor({state:'hidden'});
      const m=await row.evaluate(el=>{
        const controls=[...el.querySelectorAll('input,.select-box,.ui-switch,.row-menu-button')];
        const boxes=controls.map(n=>{const b=n.getBoundingClientRect();return {y:b.y,height:b.height,center:b.y+b.height/2};});
        const labels=[...el.querySelectorAll('.ev-schema-limits label')].map(n=>{
          const label=n.querySelector('span').getBoundingClientRect(),input=n.querySelector('input').getBoundingClientRect();
          return {overlap:label.right>input.left,inputWidth:input.width,centerDifference:Math.abs(label.y+label.height/2-input.y-input.height/2)};
        });
        return {height:el.getBoundingClientRect().height,boxes,labels};
      });
      check(Math.max(...m.boxes.map(b=>b.center))-Math.min(...m.boxes.map(b=>b.center))<.6,`${lang}/${theme}/${width}/${type}: aligned controls`);
      check(m.labels.every(l=>!l.overlap&&l.centerDifference<.6),`${lang}/${theme}/${width}/${type}: labels beside inputs`);
      if(type==='number')check(m.labels.every(l=>l.inputWidth>=60),`${lang}/${theme}/${width}: numeric bounds remain readable`);
      measurements.push({lang,theme,width,type,...m});
      if((lang==='ru'&&theme==='light'&&width===1440)||(lang==='en'&&theme==='dark'&&width===320)){
        await page.locator('.ev-schema-scroll').evaluate(el=>{el.scrollLeft=el.scrollWidth;});
        await page.locator('.ev-schema').screenshot({path:`design/baseline/widget-site-events/verification/schema-${type}-${lang}-${theme}-${width}.png`});
      }
    }
    await row.locator('.row-menu-button').click();
    const item=page.getByRole('button',{name:lang==='ru'?'Удалить поле':'Remove field',exact:true});
    await item.waitFor();
    const menu=page.getByRole('menu').filter({has:item});
    const m=await menu.evaluate(el=>{
      const button=el.querySelector('button'),s=getComputedStyle(button);
      // Layout dimensions are unaffected by the platform's opening animation.
      return {width:el.offsetWidth,itemHeight:button.offsetHeight,padding:s.padding,icon:!!button.querySelector('svg'),warning:button.classList.contains('warning')};
    });
    check(m.width===220&&m.itemHeight===33&&m.icon&&m.warning,`${lang}/${theme}/${width}: platform menu geometry and action`);
    measurements.push({lang,theme,width,menu:m});
    if(width===1440)await menu.screenshot({path:`design/baseline/widget-site-events/verification/schema-menu-${lang}-${theme}.png`});
    await item.focus();await page.keyboard.press('Escape');
    await item.waitFor({state:'hidden'});
    check(await item.isHidden(),`${lang}/${theme}/${width}: Escape closes menu`);
    await row.locator('.row-menu-button').click();await page.locator('.portal-settings-heading').click();
    await item.waitFor({state:'hidden'});
    check(await item.isHidden(),`${lang}/${theme}/${width}: outside click closes menu`);
  }
  return {checked,measurements,errors};
}
