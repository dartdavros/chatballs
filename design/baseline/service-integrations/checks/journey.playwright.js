// A ready scenario and a blank scenario enter the same editor. No API calls.
async page => {
  const errors=[],requests=[],record=r=>{if(/^https?:/.test(r.url()))requests.push(r.url());};page.on('request',record);
  const content=page.locator('.settings-content'),frames=page.locator('.si-review select').first();
  const click=name=>content.getByRole('button',{name,exact:true}).click();
  const select=async(label,value)=>{await click(label);await page.locator('.app-dropdown:visible').getByRole('button',{name:value,exact:true}).click();};
  await frames.selectOption('J01');await page.getByPlaceholder('Найти сервис').fill('Битрикс');await click('Подключить');
  await click('Проверить и подключить');
  if(!await content.getByText('Вставьте ссылку входящего вебхука.',{exact:true}).isVisible())errors.push('Required webhook');
  await content.getByLabel('Название подключения',{exact:true}).fill('Битрикс24 · Продажи');
  await content.getByPlaceholder('Вставьте ссылку вебхука').fill('https://nord.example/rest/1/preview/');await click('Проверить и подключить');
  await click('Настроить');await click('Проверить настройки');
  if(!await content.getByText('Выберите ответственного за лид.',{exact:true}).isVisible())errors.push('Required owner');
  await select('Ответственный за лид','Анна Ким');await click('Проверить настройки');await click('Включить сценарий');await click('Изменить сценарий');
  if(await frames.inputValue()!=='X01'||await content.locator('.si-sortable').count()!==2)errors.push('Preset did not enter common editor');
  await content.getByLabel('Название сценария',{exact:true}).fill('Передать обращение в продажи');
  await click('Добавить шаг');await click('Выбрать действие');await content.getByLabel('Метка',{exact:true}).fill('Передано в CRM');await click('Применить к сценарию');
  await click('Настроить: 1');await select('Ответственный за лид','Дмитрий Орлов');await click('Отмена');await click('Настроить: 1');
  if(!(await content.getByRole('button',{name:'Ответственный за лид',exact:true}).innerText()).includes('Анна Ким'))errors.push('Step cancel changed parameters');
  await select('Ответственный за лид','Дмитрий Орлов');await click('Применить к сценарию');await click('Сохранить черновик');await click('Проверить сценарий');await click('Включить сценарий');
  await click('К подключению');
  if(!await content.getByText('Передать обращение в продажи',{exact:true}).isVisible())errors.push('Saved scenario missing in profile');
  await frames.selectOption('J11');await click('Ещё одно подключение Битрикс24');
  await content.getByLabel('Название подключения',{exact:true}).fill('Битрикс24 · Поддержка');await content.getByPlaceholder('Вставьте ссылку вебхука').fill('https://support.example/rest/2/preview/');await click('Проверить и подключить');
  if(await content.getByText('Передать обращение в продажи',{exact:true}).count())errors.push('First connection scenario leaked into second connection');
  await frames.selectOption('J10');
  for(const name of ['Битрикс24 · Продажи','Битрикс24 · Поддержка'])if(!await content.getByRole('button',{name,exact:true}).isVisible())errors.push('Missing independent connection '+name);
  await content.getByRole('button',{name:'Битрикс24 · Продажи',exact:true}).click();
  if(!await content.getByRole('heading',{name:'Битрикс24 · Продажи',exact:true}).isVisible())errors.push('Connection selection lost');
  if(!await content.getByText('Передать обращение в продажи',{exact:true}).isVisible())errors.push('First connection scenario lost');
  page.off('request',record);return{errors,requests,verified:'catalog, required fields, ready copy, common editor, step apply/cancel, draft/enable, two connections of one service'};
}
