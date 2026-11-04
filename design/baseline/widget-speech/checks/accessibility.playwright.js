async (page) => {
  const errors = [], verified = [];
  const select = page.locator('.sp-review select');
  await select.nth(3).selectOption('en');
  await select.nth(2).selectOption('dark');
  await select.nth(1).selectOption('320');
  const first = await select.nth(0).locator('option').nth(1).getAttribute('value');
  const id = first.startsWith('S') ? 'S11' : first.startsWith('D') ? 'D16' : 'P11';
  await select.nth(0).selectOption(id);
  await page.setViewportSize({ width: 360, height: 900 });
  const screen = page.locator('[data-screen]');
  const narrow = await screen.evaluate(el => ({ width: el.clientWidth, scroll: el.scrollWidth }));
  if (narrow.scroll > narrow.width + 1) errors.push('Mobile screen overflows');
  await screen.locator('button:not([disabled]),textarea,input:not([disabled])').first().focus();
  const focus = [];
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab');
    focus.push(await page.evaluate(() => ({ tag: document.activeElement.tagName,
      outline: getComputedStyle(document.activeElement).outlineStyle,
      label: document.activeElement.getAttribute('aria-label') || document.activeElement.textContent?.slice(0,60) })));
  }
  if (!focus.some(item => item.outline === 'solid')) errors.push('No visible keyboard focus');
  verified.push('360px browser viewport, English errors, keyboard Tab and visible focus');
  await page.setViewportSize({ width: 1510, height: 1120 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  const zoom = await screen.evaluate(el => {
    const box = el.getBoundingClientRect();
    return { renderedWidth: box.width, width: el.clientWidth, scroll: el.scrollWidth,
      inputs: [...el.querySelectorAll('input,textarea,button')].filter(n => n.getClientRects().length)
        .filter(n => n.getBoundingClientRect().right > box.right + 1).map(n => n.className) };
  });
  if (zoom.scroll > zoom.width + 1 || zoom.inputs.length) errors.push({ zoom });
  await screen.screenshot({ path: `design/baseline/widget-speech/verification/${id}-en-dark-zoom200.png`, animations: 'disabled' });
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  verified.push('200% CSS zoom at 320 CSS px; controls remain inside the frame');
  return { check: 'keyboard-scale', errors, verified, focus };
}
