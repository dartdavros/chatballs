// Checks design navigation and real shared controls, never service/API behavior.
async (page) => {
  const errors = [];
  const requests = [];
  const record = request => { if (/\/api\//.test(request.url())) requests.push(request.url()); };
  page.on('request', record);
  const select = page.locator('.si-review select');
  await select.nth(1).selectOption('1440');
  await select.nth(2).selectOption('light');
  await select.nth(0).selectOption('C01');
  await page.locator('.settings-content').getByRole('button', { name: 'Подключить сервис', exact: true }).click();
  if (await select.first().inputValue() !== 'C03') errors.push('connection → catalog');
  await page.getByPlaceholder('Найти адаптер').fill('MCP');
  if (await page.locator('.si-line').count() !== 1) errors.push('adapter search');
  await page.locator('.si-line').getByRole('button', { name: 'Выбрать', exact: true }).click();
  if (await select.first().inputValue() !== 'C11') errors.push('MCP catalog → MCP creation');
  await select.first().selectOption('C04');
  await page.getByRole('button', { name: 'Способ доступа', exact: true }).click();
  await page.locator('.app-dropdown').getByRole('button', { name: 'OAuth', exact: true }).click();
  if (await select.first().inputValue() !== 'A03') errors.push('shared SelectField → OAuth authorization');
  await select.first().selectOption('C05');
  const toggle = page.getByRole('switch');
  const before = await toggle.getAttribute('aria-checked');
  await toggle.click();
  if (await toggle.getAttribute('aria-checked') === before) errors.push('shared SwitchButton');
  await select.first().selectOption('C06');
  await page.getByRole('button', { name: 'Создать редактируемую копию', exact: true }).click();
  if (await select.first().inputValue() !== 'E02') errors.push('template → editor');
  await page.getByRole('button', { name: 'Добавить шаг', exact: true }).click();
  if (await select.first().inputValue() !== 'B01') errors.push('editor → block catalog');
  await page.locator('.si-line').filter({ hasText: 'Ветвление' }).getByRole('button', { name: 'Выбрать', exact: true }).click();
  if (await select.first().inputValue() !== 'B02') errors.push('block catalog → branch');
  await select.first().selectOption('V01');
  await page.getByPlaceholder('Найти поле').fill('Электронная');
  if (await page.locator('.si-table-wrap tbody tr').count() !== 1) errors.push('field search');
  await page.locator('.si-table-wrap').getByRole('button', { name: 'Выбрать', exact: true }).click();
  await page.getByRole('button', { name: 'Применить значение', exact: true }).click();
  if (await select.first().inputValue() !== 'V02') errors.push('binding → parameter');
  const scroll = [];
  for (const width of ['1440', '1024']) {
    await select.nth(1).selectOption(width);
    for (const id of ['E02', 'V02', 'L04', 'P01', 'B09']) {
      await select.first().selectOption(id);
      scroll.push(await page.locator('.settings-content').evaluate((e, id) => {
        e.scrollTop = e.scrollHeight;
        return { id, height: e.scrollHeight, visible: e.clientHeight, bottom: e.scrollHeight - e.clientHeight - e.scrollTop < 2 };
      }, id));
    }
  }
  if (scroll.some(s => !s.bottom)) errors.push('unreachable form bottom');
  page.off('request', record);
  return { errors, apiRequests: requests, scroll };
}
