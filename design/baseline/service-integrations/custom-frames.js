window.CustomFrames = function () {
  const { h, frame } = window.ServiceParts, t = window.jt, E = window.CustomEditor, F = window.CustomForms;
  const leads = { X02: 'paletteLead', X03: 'actionFormLead', X04: 'conditionsLead', X05: 'blockLead', X06: 'reviewLeadCustom', X07: '', X08: 'launchLead', X09: '',X10:'',X11:'relationshipsHelp',X12:'conflictHelp' };
  const create = (id, title, heading, component) => frame(id, title, t(heading), t(leads[id] ?? 'customLead'), [h(component)], { root: true });
  return [
    create('X01','Свой сценарий · редактор','customTitle',E.Editor),
    create('X02','Свой сценарий · выбор вида шага','customPalette',E.Palette),
    create('X03','Свой сценарий · действие и значения','customConfigure',window.CustomAction),
    create('X04','Свой сценарий · условия','conditions',window.ConditionEditor.Conditions),
    create('X05','Свой сценарий · параметры блока','customConfigure',F.BlockForm),
    create('X06','Свой сценарий · проверка перед включением','customReview',E.Review),
    create('X07','Свой сценарий · сохранённая версия','customSaved',E.Saved),
    create('X08','Свой сценарий · способы запуска и доступ','customLaunch',window.LaunchSettings.Launch),
    create('X09','Свой сценарий · несохранённые изменения','customUnsaved',E.Unsaved),
    create('X10','Свой сценарий · входные параметры и результаты','schemaTab',window.SchemaEditor.Schema),
    create('X11','Свой сценарий · связи и синхронизация','syncTab',window.SyncSettings.Sync),
    create('X12','Связи · решение конфликта','conflictTitle',window.SyncSettings.Conflict),
  ];
};
