// Exercises the design state only; no service requests or execution.
async page => {
  page.setDefaultTimeout(10000);
  const errors = [], requests = [];
  const record = req => { if (/^https?:/.test(req.url())) requests.push(req.url()); };
  page.on('request', record);
  const content = page.locator('.settings-content'), frames = page.locator('.si-review select').first();
  const click = async name => (await page.getByRole('dialog').count() ? page.getByRole('dialog') : content).getByRole('button', { name, exact: true }).click();
  const select = async (label, option) => {
    await click(label); await page.locator('.app-dropdown').getByRole('button', { name: option, exact: true }).click();
  };
  const kind = async name => {
    if (name === 'Действие') return click('Выбрать действие');
    await click('Условия, ожидания и другие блоки');
    await content.locator('.si-line').filter({ has: page.locator('strong').getByText(name, { exact: true }) }).getByRole('button', { name: 'Настроить', exact: true }).click();
  };
  const add = async name => { await content.getByRole('button', { name: 'Добавить шаг', exact: true }).last().click(); await kind(name); };
  const apply = () => click('Применить к сценарию');
  await frames.selectOption('J03'); await click('Создать свой сценарий');
  await click('Проверить сценарий');
  if (!await content.getByRole('button', { name: 'Включить сценарий', exact: true }).isDisabled()) errors.push('Empty scenario can enable');
  await click('Вернуться в редактор');
  await content.getByLabel('Название сценария', { exact: true }).fill('Передать обращение');
  await add('Действие'); await select('Подключение', 'Битрикс24 · Отдел продаж');
  await select('Откуда взять значение', 'Из диалога'); await select('Название лида', 'Тема диалога'); await apply();
  await add('Действие'); await select('Раздел Chatballs','Контакты'); await select('Действие', 'Связать запись с диалогом');
  await select('Откуда взять значение', 'Результат предыдущего шага'); await select('Предыдущий шаг', 'Создать лид'); await apply();
  const moveBefore = async (sourceIndex, targetIndex) => {
    const source = content.locator('.si-sortable').nth(sourceIndex), target = content.locator('.si-sortable').nth(targetIndex);
    await source.locator('.site-field-grip').dragTo(target, { targetPosition: { x: 90, y: 5 } });
  };
  await moveBefore(1, 0);
  await click('Проверить сценарий');
  if (!await content.getByText('Источник результата должен быть предыдущим шагом в этой же ветви.', { exact: true }).isVisible()) errors.push('Invalid reorder not detected');
  await click('Вернуться в редактор');
  await moveBefore(1, 0);
  await add('Ветвление'); await apply();
  await click('Проверить сценарий');
  if (!await content.getByText('Добавьте шаги во все ветви блока.', { exact: true }).isVisible()) errors.push('Empty branches accepted');
  await click('Вернуться в редактор');
  for (const branch of ['Если да', 'Иначе']) {
    await content.locator('.si-nested').filter({ has: page.getByRole('heading', { name: branch, exact: true }) }).getByRole('button', { name: 'Добавить шаг', exact: true }).click();
    await kind('Действие'); await content.getByLabel('Метка', { exact: true }).fill(branch); await apply();
  }
  await click('Сохранить черновик'); await click('Вернуться в редактор');
  await content.getByLabel('Название сценария', { exact: true }).fill('Не сохранять');
  await click('Отмена');
  if (await frames.inputValue() !== 'X09') errors.push('Missing unsaved guard');
  await click('Выйти без сохранения');
  await content.locator('.si-card').filter({ has: page.getByText('Передать обращение', { exact: true }) }).getByRole('button', { name: 'Изменить сценарий', exact: true }).click();
  if (await content.getByLabel('Название сценария', { exact: true }).inputValue() !== 'Передать обращение') errors.push('Discard failed');
  await click('Проверить сценарий'); await click('Включить сценарий');
  if (!await content.getByText('Сценарий включён', { exact: true }).isVisible()) errors.push('Enable failed');
  await click('Вернуться в редактор');
  await add('Ожидание времени'); await apply();
  if (await frames.inputValue() !== 'X05') errors.push('Empty wait accepted');
  await content.getByLabel('Минуты', { exact: true }).fill('15'); await apply();
  await add('Ожидание события'); await content.getByLabel('Срок ожидания, минуты', { exact: true }).fill('60'); await apply();
  await add('Ожидание подтверждения'); await content.getByLabel('Что показать сотруднику', { exact: true }).fill('Подтвердите передачу');
  await content.getByLabel('Срок ожидания, минуты', { exact: true }).fill('30'); await apply();
  for (const name of ['Перебор списка','Параллельные ветви','Вложенный сценарий','Обработка ошибок']) { await add(name); await apply(); }
  await click('Проверить сценарий');
  if (!await content.getByRole('button', { name: 'Включить сценарий', exact: true }).isDisabled()) errors.push('Incomplete nested blocks accepted');
  await click('Вернуться в редактор');
  const count = await content.locator('.si-block').count();
  await content.locator('.si-sortable .row-menu-button').last().click();
  await page.getByRole('menuitem', { name: 'Копировать', exact: true }).click();
  if (await content.locator('.si-block').count() !== count + 1) errors.push('Copy failed');
  await content.locator('.si-sortable .row-menu-button').last().click();
  await page.getByRole('menuitem', { name: 'Удалить шаг', exact: true }).last().click();
  if (await content.locator('.si-block').count() !== count) errors.push('Remove failed');
  page.off('request', record);
  return { errors, requests, verified: 'create, typed step result, reorder validation, nested branches, draft, discard, enable, all block forms, required wait fields, copy, remove' };
}
