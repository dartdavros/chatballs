window.ServiceFrames.journey = function () {
  const { h, frame, note, actions } = window.ServiceParts;
  const t = window.jt, C = window.JourneyConnect, S = window.JourneyScenario;
  const { Action } = window.Journey;
  return [
    frame('J01', 'Выбрать сервис', t('catalogTitle'), t('catalogLead'), [h(C.Catalog)], { backFrame: 'J10', backLabel: t('services') }),
    frame('J02', 'Подключить Битрикс24', t('connectTitle'), t('connectLead'), [h(C.Connect)], { backFrame: 'J01', backLabel: t('catalogTitle') }),
    frame('J03', 'Подключение → полезный сценарий', t('defaultName'), t('serviceLead'), [h(C.Connected)], { backFrame: 'J10', backLabel: t('services') }),
    frame('J04', 'Настроить готовый сценарий', t('setupTitle'), t('setupLead'), [h(S.Setup)], { backFrame: 'J03', backLabel: t('bitrix') }),
    frame('J05', 'Проверить перед включением', t('reviewTitle'), t('reviewLead'), [h(S.Review)], { backFrame: 'J04', backLabel: t('change') }),
    frame('J06', 'Сценарий включён', t('setupTitle'), t('serviceLead'), [h(S.Enabled)], { backFrame: 'J03', backLabel: t('bitrix') }),
    frame('J10', 'Подключённые сервисы', t('integrations'), t('servicesLead'), [h(S.Services)], { root: true }),
    frame('J11', 'Доступ к подключению', t('defaultName'), t('serviceLead'), [h(C.ConnectionSettings)], { backFrame: 'J03', backLabel: t('bitrix') }),
    frame('J12', 'Нет разрешения на CRM', t('connectTitle'), t('connectLead'), [
      note(t('accessError'), t('accessErrorHelp'), 'error'), actions(h(Action, { label: 'retry', primary: true, to: 'J02' })),
    ], { backFrame: 'J01', backLabel: t('catalogTitle') }),
    frame('J13', 'Сценарий несовместим с режимом CRM', t('setupTitle'), t('serviceLead'), [
      note(t('leadUnavailable'), t('leadUnavailableHelp'), 'warn'), actions(h(Action, { label: 'toService', to: 'J03' })),
    ], { backFrame: 'J03', backLabel: t('bitrix') }),
  ].map(item => ['J01', 'J09', 'J10'].includes(item.id) ? item : { ...item, service: 'bitrix' }).concat(window.VendorFrames(), window.CustomFrames(),window.ReviewStates(),window.AccessMethodFrames());
};
