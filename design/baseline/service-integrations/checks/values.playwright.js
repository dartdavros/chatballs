// Structured values must be editable and readable without JSON.
async page=>{
  const errors=[],content=page.locator('.settings-content'),frames=page.locator('.si-review select').first();
  const click=name=>content.getByRole('button',{name,exact:true}).click();
  const select=async(scope,label,value)=>{await scope.getByRole('button',{name:label,exact:true}).click();await page.locator('.app-dropdown:visible').getByRole('button',{name:value,exact:true}).click();await page.locator('.app-dropdown:visible').waitFor({state:'hidden'});};
  await frames.selectOption('J06');await click('Изменить сценарий');await click('Параметры');await click('Добавить результат');
  const output=content.locator('.si-card').filter({has:page.getByRole('heading',{name:'Что вернуть после выполнения',exact:true})});
  await output.getByLabel('Название',{exact:true}).fill('Результат');await select(output,'Тип значения','Объект с полями');await select(output,'Откуда взять значение','Задать значение');
  await output.getByRole('button',{name:'Добавить поле объекта',exact:true}).click();await output.getByLabel('Название',{exact:true}).last().fill('Принято');
  await output.getByRole('button',{name:'Тип значения',exact:true}).last().click();await page.locator('.app-dropdown:visible').getByRole('button',{name:'Да или нет',exact:true}).click();await page.locator('.app-dropdown:visible').waitFor({state:'hidden'});
  await select(output,'Значение','Да');await click('Применить настройки');await click('Проверить сценарий');
  if(!await content.getByText('Принято: Да',{exact:true}).isVisible())errors.push('Object value missing in review');await click('Вернуться в редактор');await click('Параметры');await click('Добавить результат');
  const list=output.locator('.si-card').last();await list.getByLabel('Название',{exact:true}).fill('Сообщения');await select(list,'Тип значения','Список');await select(list,'Откуда взять значение','Задать значение');
  for(const value of ['Готово','Проверено']){await list.getByRole('button',{name:'Добавить элемент списка',exact:true}).click();await list.getByLabel('Значение',{exact:true}).last().fill(value);}
  await click('Применить настройки');await click('Проверить сценарий');
  if(!await content.getByText('Готово; Проверено',{exact:true}).isVisible())errors.push('List value missing in review');
  if(/object-value|list-value|parameter-\d/.test(await content.innerText()))errors.push('Internal value leaked into UI');
  return{errors,verified:'object with boolean field, list with text items, save and human-readable review without JSON'};
}
