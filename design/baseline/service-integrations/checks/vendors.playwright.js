// Static design interactions only. Never contact a vendor or enter real secrets.
async (page) => {
  page.setDefaultTimeout(10000);
  const errors = [], requests = [];
  const record = request => { if (/^https?:/.test(request.url())) requests.push(request.url()); };
  page.on('request', record);
  const frames = page.locator('.si-review select').first(), content = page.locator('.settings-content');
  const click = name => content.getByRole('button', { name, exact: true }).click();
  const select = async (label, name) => {
    await click(label);
    await page.locator('.app-dropdown').getByRole('button', { name, exact: true }).click();
  };
  const at = async id => { if (await frames.inputValue() !== id) errors.push(`Expected ${id}`); };
  await frames.selectOption('J01');
  await page.getByPlaceholder('Найти сервис').fill('amo');
  await click('Подключить'); await at('Q01');
  await content.getByLabel('Название подключения', { exact: true }).fill('amoCRM · Продажи тест');
  await content.getByLabel('Адрес аккаунта', { exact: true }).fill('https://crm.example');
  await click('Продолжить в amoCRM'); await at('Q02');
  await page.getByRole('button', { name: 'Показать отказ', exact: true }).click(); await at('Q07');
  await click('Исправить подключение');
  await click('Продолжить в amoCRM');
  await page.getByRole('button', { name: 'Показать успешный возврат', exact: true }).click();
  await click('Подключить этот аккаунт'); await at('Q04');
  if (!await content.getByRole('heading', { name: 'amoCRM · Продажи тест', exact: true }).isVisible()) errors.push('amo name lost');
  await click('Настроить'); await at('Q05');
  await click('Проверить настройки');
  if (!await content.getByText('Заполните обязательные настройки перед включением.', { exact: true }).isVisible()) errors.push('amo owner required');
  await select('Воронка', 'Партнёры');
  if (!(await content.getByRole('button', { name: 'Этап сделки', exact: true }).innerText()).includes('Новый партнёр')) errors.push('Dependent stage not updated');
  await select('Ответственный за сделку', 'Анна Ким');
  await click('Проверить настройки'); await at('Q06');
  await click('Включить сценарий'); await at('Q10');
  await click('Изменить сценарий'); await at('X01'); await click('Настроить: 1');
  await select('Ответственный за сделку', 'Дмитрий Орлов');
  await click('Отмена'); await click('Отмена'); await at('Q04');
  await frames.selectOption('Q10');
  if (!await content.getByText('Анна Ким', { exact: true }).isVisible()) errors.push('Cancel changed enabled settings');
  await frames.selectOption('Q11'); await click('Подключить по токену');
  await click('Проверить и подключить');
  if (!await content.getByText('Укажите секрет доступа.', { exact: true }).isVisible()) errors.push('Token required');
  await content.getByPlaceholder('Вставьте новый токен').fill('preview-only');
  await click('Проверить и подключить'); await at('Q04');
  await frames.selectOption('J01');
  await page.getByPlaceholder('Найти сервис').fill('Mindbox'); await click('Подключить'); await at('D01');
  await click('Сохранить подключение');
  if (!await content.getByText('Укажите точку интеграции.', { exact: true }).isVisible()) errors.push('Endpoint required');
  await content.getByLabel('Название подключения', { exact: true }).fill('Mindbox · Проверка');
  await content.getByLabel('Адрес API проекта', { exact: true }).fill('https://mindbox.example');
  await content.getByPlaceholder('Идентификатор из Mindbox').fill('Preview');
  await content.getByPlaceholder('Вставьте новый ключ').fill('preview-only');
  await click('Сохранить подключение'); await at('D02');
  await frames.selectOption('D06');
  if (!await content.getByRole('button', { name: 'Включить сценарий', exact: true }).isDisabled()) errors.push('Unchecked Mindbox can enable');
  await frames.selectOption('D02'); await click('Проверить доступ'); await at('D03');
  await click('Проверить чтение');
  if (!await content.getByText('Укажите идентификатор клиента для проверки.', { exact: true }).isVisible()) errors.push('Read ID required');
  await content.getByLabel(/^Идентификатор существующего клиента/).fill('preview-customer');
  await click('Проверить чтение'); await at('D04');
  await click('Настроить'); await click('Проверить настройки'); await click('Включить сценарий'); await at('D10');
  await frames.selectOption('J10');
  for (const name of ['amoCRM · Продажи тест', 'Mindbox · Проверка']) {
    if (!await content.getByRole('button', { name, exact: true }).isVisible()) errors.push(`Missing connection ${name}`);
  }
  await frames.selectOption('D01');
  if (await content.getByPlaceholder('Вставьте новый ключ').inputValue()) errors.push('Secret retained');
  page.off('request', record);
  return { errors, requests, verified: 'OAuth outcomes, token fallback, required fields, dependent stage, preset enable, cancel, Mindbox read gate, connection list, secret discard' };
}
