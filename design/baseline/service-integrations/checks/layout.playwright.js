// Run with Skaro Playwright browser_run_code_unsafe after loading a built baseline.
async (page) => {
  const errors=[]; const report=[];
  const ids=await page.locator('.si-review select').nth(0).locator('option').evaluateAll(xs=>xs.map(x=>x.value).filter(x=>x!=='all'));
  for(const width of [1440,1024]) for(const theme of ['light','dark']) for(const accent of ['#0f9b8e','#1677ff','#6d5dfc','#e8590c']) {
    await page.setViewportSize({width,height:1100});
    await page.locator('.si-review select').nth(1).selectOption(String(width));
    await page.locator('.si-review select').nth(2).selectOption(theme);
    await page.locator('.si-review select').nth(3).selectOption(accent);
    for(const id of ids) {
      await page.locator('.si-review select').nth(0).selectOption(id);
      const result=await page.locator('.si-screen').evaluate(screen=>{const r=screen.getBoundingClientRect();return {
        width:screen.clientWidth,height:screen.clientHeight,
        overflow:[...screen.querySelectorAll('*')].filter(e=>{const b=e.getBoundingClientRect();return b.width&&b.right>r.right+2}).map(e=>({tag:e.tagName,class:e.className,text:e.textContent.slice(0,50)})),
        internal:[...screen.querySelectorAll('td,.si-notice,.si-field')].filter(e=>e.scrollWidth>e.clientWidth+3).map(e=>({tag:e.tagName,text:e.textContent.slice(0,50)})),
        sidebar:screen.querySelector('.hub-sidebar').getBoundingClientRect().width,
        submenu:screen.querySelector('.settings-subnav').getBoundingClientRect().width,
        padding:getComputedStyle(screen.querySelector('.settings-content-inner')).padding,
        heading:getComputedStyle(screen.querySelector('.settings-head h2')).fontSize,
        nativeSelects:screen.querySelectorAll('select').length,
        inventedHeader:screen.querySelectorAll('.si-page-head,.si-breadcrumb').length,
        toggleLines:[...screen.querySelectorAll('.si-inline-toggle')].some(e=>getComputedStyle(e).borderBottomWidth!=='0px'),
        forbidden:/SPEC-|ADR-|DG-|OWNER|ADMIN|PROTECT|allowCheckoutActions/.test(screen.innerText),
        images:[...screen.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0)
      }});
      report.push({id,width,theme,accent,height:result.height});
      if(result.width!==width||result.overflow.length||result.internal.length||result.forbidden||!result.images
        ||result.sidebar!==(width===1024?60:220)||result.submenu!==240||result.padding!=='28px 40px 48px'
        ||result.heading!=='20px'||result.nativeSelects||result.inventedHeader||result.toggleLines) errors.push({id,width,theme,accent,...result});
    }
  }
  return {count:report.length,ids,errors};
}
