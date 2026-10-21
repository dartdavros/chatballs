// Run after custom.playwright.js: measure the populated editor, not empty placeholders.
async page => {
  const errors = [], measurements = [], frames = page.locator('.si-review select');
  const content = page.locator('.settings-content');
  for (const width of [1024,1440]) for (const theme of ['light','dark']) {
    await frames.nth(1).selectOption(String(width)); await frames.nth(2).selectOption(theme);
    for (const frame of ['X01','X03','X04','X08','J02','J04','Q01','D01','J10']) {
      await frames.first().selectOption(frame);
      const result = await content.evaluate(root => {
        const fields = [...root.querySelectorAll('.readonly-field')].map(el => ({ width: el.getBoundingClientRect().width,
          limit: el.querySelector('input[type=number]') ? 160 : el.classList.contains('wide') || el.querySelector('textarea') ? 480 : 320 }));
        const actionCells = [...root.querySelectorAll('td.si-table-actions')].map(el => {
          const rect = el.getBoundingClientRect(), button = el.querySelector('button').getBoundingClientRect();
          return Math.abs(rect.right - parseFloat(getComputedStyle(el).paddingRight) - button.right);
        });
        return { fields, actionCells, overflow: [...root.querySelectorAll('.si-sortable,.si-line,.si-nested')].filter(e => e.scrollWidth > e.clientWidth + 2).length,
          lines: [...root.querySelectorAll('.si-line')].some(e => getComputedStyle(e).borderBottomWidth !== '0px') };
      });
      measurements.push({ width, theme, frame, ...result });
      if (result.fields.some(f => f.width > f.limit + 1) || result.actionCells.some(gap => gap > 1) || result.overflow || result.lines) errors.push({ width, theme, frame, ...result });
    }
  }
  await frames.first().selectOption('X01'); await frames.nth(1).selectOption('1024');
  const before = await content.locator('.si-sortable').evaluateAll(rows => rows.map(r => r.dataset.stepId));
  const grip = content.getByRole('button', { name: 'Переместить шаг: 2', exact: true });
  await grip.scrollIntoViewIfNeeded();
  const from = await grip.boundingBox(), target = await content.locator('.si-sortable').first().boundingBox();
  await page.mouse.move(from.x + 7, from.y + 7); await page.mouse.down();
  await page.mouse.move(from.x + 8, from.y + 15, { steps: 3 });
  await page.mouse.move(target.x + 80, target.y + 3, { steps: 8 });
  await page.mouse.move(target.x + 81, target.y + 4);
  const dragging = await content.locator('.si-sortable.is-dragging').evaluate(el => getComputedStyle(el).boxShadow !== 'none');
  const insertion = await content.locator('.si-drop-slot.is-target').count();
  if (!dragging || insertion !== 1) errors.push({ dragging, insertion });
  await page.keyboard.press('Escape'); await page.mouse.up();
  const after = await content.locator('.si-sortable').evaluateAll(rows => rows.map(r => r.dataset.stepId));
  if (JSON.stringify(before) !== JSON.stringify(after) || await content.locator('.is-dragging,.is-target').count()) errors.push('Escape did not cancel drag cleanly');
  await content.getByRole('button', { name: 'Переместить шаг: 2', exact: true }).focus();
  await page.keyboard.press('ArrowUp');
  if (await content.locator('.si-sortable').first().getAttribute('data-step-id') !== before[1]) errors.push('Keyboard reorder failed');
  await page.keyboard.press('ArrowDown');
  await content.locator('.row-menu-button').first().click(); await page.keyboard.press('Escape');
  if (await page.locator('.app-dropdown:visible').count()) await page.locator('.app-dropdown:visible').waitFor({state:'hidden'});
  return { errors, measuredScreens: measurements.length, verified: 'field widths, right-aligned actions, no row separators, populated nested editor overflow, drag shadow and insertion marker, Escape cancellation, keyboard reorder, menu Escape' };
}
