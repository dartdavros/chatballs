// Verify choices, transformation settings and their persistence through the editor.
async page=>{
  const errors=[],c=page.locator('.settings-content'),frames=page.locator('.si-review select').first();
  const click=name=>c.getByRole('button',{name,exact:true}).click();
  const select=async(root,label,value)=>{await root.getByRole('button',{name:label,exact:true}).last().click();await page.locator('.app-dropdown:visible').getByRole('button',{name:value,exact:true}).click();await page.locator('.app-dropdown:visible').waitFor({state:'hidden'});};
  await frames.selectOption('J06');await click('Изменить сценарий');await click('Параметры');await click('Добавить параметр');
  const input=c.locator('.si-card').filter({has:page.getByRole('heading',{name:'Что спросить при запуске',exact:true})});
  await input.getByLabel('Название',{exact:true}).fill('Тип обращения');await input.getByRole('switch',{name:'Ограничить выбор значениями',exact:true}).click();
  await click('Применить настройки');if(await frames.inputValue()!=='X10')errors.push('Empty choices accepted');
  for(const value of ['Продажи','Поддержка']){await input.getByRole('button',{name:'Добавить значение',exact:true}).click();await input.getByLabel('Разрешённое значение',{exact:true}).last().fill(value);}
  await click('Применить настройки');await click('Параметры');
  const saved=await input.getByLabel('Разрешённое значение',{exact:true}).evaluateAll(xs=>xs.map(x=>x.value));
  if(saved.join('|')!=='Продажи|Поддержка')errors.push('Choices lost');
  const output=c.locator('.si-card').filter({has:page.getByRole('heading',{name:'Что вернуть после выполнения',exact:true})});
  for(const [name,type,transform,value] of [['Текст','Текст','Объединить значения','Готово'],['Дата','Дата','Привести дату к часовому поясу','2026-10-21'],['Поля','Объект с полями','Выбрать поля объекта',''],['Список','Список','Отобрать элементы списка','']]){
    await click('Добавить результат');const p=output.locator('.si-parameter-head').last().locator('..');
    await p.getByLabel('Название',{exact:true}).fill(name);await select(p,'Тип значения',type);await select(p,'Откуда взять значение','Задать значение');
    if(type==='Объект с полями'){
      await p.getByRole('button',{name:'Добавить поле объекта',exact:true}).click();await p.getByLabel('Название',{exact:true}).last().fill('Статус');await p.getByLabel('Значение',{exact:true}).fill('Готово');
    }else if(type==='Список'){
      await p.getByRole('button',{name:'Добавить элемент списка',exact:true}).click();await p.getByLabel('Значение',{exact:true}).fill('Готово');
    }else await p.getByLabel('Значение',{exact:true}).fill(value);
    await select(p,'Преобразование',transform);
    if(type==='Текст')await p.getByLabel('Разделитель значений',{exact:true}).fill('; ');
    if(type==='Дата')await select(p,'Часовой пояс результата','Europe/Berlin · Берлин');
    if(type==='Объект с полями'){await p.getByRole('button',{name:'Добавить поле',exact:true}).click();await p.getByLabel('Поле объекта',{exact:true}).fill('Статус');}
    if(type==='Список'){await p.getByLabel('Поле элемента списка',{exact:true}).fill('Статус');await select(p,'Оставлять элементы, если','Поле равно значению');await p.getByLabel('Значение для сравнения',{exact:true}).fill('Готово');}
  }
  await click('Применить настройки');await click('Параметры');
  if(await output.getByLabel('Поле объекта',{exact:true}).inputValue()!=='Статус'||await output.getByLabel('Значение для сравнения',{exact:true}).inputValue()!=='Готово')errors.push('Transformation settings lost');
  await click('Отмена');await click('Проверить сценарий');
  const text=await c.innerText();if(!text.includes('Europe/Berlin')||!text.includes('Выбрать поля объекта: Статус')||!text.includes('Поле равно значению Готово'))errors.push('Transformations missing in review');
  return{errors,verified:'choice validation and persistence; text/date/object/list transformation settings and readable review'};
}
