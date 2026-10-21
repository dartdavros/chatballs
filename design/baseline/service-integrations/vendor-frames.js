window.VendorFrames = function () {
  const { h, frame, note, actions } = window.ServiceParts, t = window.jt;
  const { Action } = window.Journey, A = window.AmoConnection, M = window.MindboxConnection, S = window.VendorScenarios;
  const options = (service, backFrame, extra = {}) => ({ service, backFrame,
    backLabel: t(backFrame === 'J01' ? 'catalogTitle' : backFrame === 'J10' ? 'services' : service), ...extra });
  const issue = (title, help, to, label = 'retry') => [note(t(title), t(help), 'warn'), actions(h(Action, { label, primary: true, to }))];
  return [
    frame('Q01', 'amoCRM · OAuth или токен', t('amoConnect'), t('amoLead'), [h(A.Connect)], options('amo', 'J01')),
    frame('Q02', 'amoCRM · ожидание разрешения', t('amoConnect'), t('amoLead'), [h(A.Waiting)], options('amo', 'Q01')),
    frame('Q03', 'amoCRM · аккаунт после возврата', t('oauthConfirm'), t('amoLead'), [h(A.Confirm)], options('amo', 'Q01')),
    frame('Q04', 'amoCRM · готовый сценарий', t('amoName'), t('amoLead'), [h(S.Profile, { service: 'amo' })], options('amo', 'J10', { vendorName: 'amo' })),
    frame('Q05', 'amoCRM · параметры сделки', t('amoPreset'), t('presetSettings'), [h(S.Setup, { service: 'amo' })], options('amo', 'Q04')),
    frame('Q06', 'amoCRM · проверить и включить', t('reviewTitle'), t('amoPreset'), [h(S.Review, { service: 'amo' })], options('amo', 'Q05')),
    frame('Q07', 'amoCRM · отказ в разрешении', t('amoConnect'), t('amoLead'), issue('oauthDenied', 'oauthDeniedHelp', 'Q01'), options('amo', 'J01')),
    frame('Q08', 'amoCRM · устаревший или чужой возврат', t('amoConnect'), t('amoLead'), issue('oauthExpired', 'oauthExpiredHelp', 'Q01'), options('amo', 'J01')),
    frame('Q09', 'amoCRM · восстановление доступа', t('amoName'), t('amoLead'), issue('accessLost', 'accessLostHelp', 'Q01', 'restoreAccess'), options('amo', 'J10')),
    frame('Q10', 'amoCRM · сценарий включён', t('amoPreset'), t('amoLead'), [h(S.Review, { service: 'amo', enabled: true })], options('amo', 'Q04')),
    frame('Q11', 'amoCRM · OAuth не настроен в установке', t('amoConnect'), t('amoLead'), [h(A.Unconfigured)], options('amo', 'J01')),
    frame('D01', 'Mindbox · точка интеграции и ключ', t('mindboxConnect'), t('mindboxLead'), [h(M.Connect)], options('mindbox', 'J01')),
    frame('D02', 'Mindbox · сохранено без проверки', t('mindboxName'), t('mindboxLead'), [h(M.Saved)], options('mindbox', 'J10', { vendorName: 'mindbox' })),
    frame('D03', 'Mindbox · проверка только чтением', t('checkAccess'), t('mindboxLead'), [h(M.Check)], options('mindbox', 'D02')),
    frame('D04', 'Mindbox · готовый сценарий', t('mindboxName'), t('mindboxLead'), [h(S.Profile, { service: 'mindbox' })], options('mindbox', 'J10', { vendorName: 'mindbox' })),
    frame('D05', 'Mindbox · данные связанного клиента', t('mindboxPreset'), t('presetSettings'), [h(S.Setup, { service: 'mindbox' })], options('mindbox', 'D04')),
    frame('D06', 'Mindbox · проверить и включить', t('reviewTitle'), t('mindboxPreset'), [h(S.Review, { service: 'mindbox' })], options('mindbox', 'D05')),
    frame('D07', 'Mindbox · ключ не принят', t('mindboxConnect'), t('mindboxLead'), issue('invalidSecret', 'invalidSecretHelp', 'D01'), options('mindbox', 'D02')),
    frame('D08', 'Mindbox · сервис недоступен', t('mindboxName'), t('mindboxLead'), issue('serviceUnavailable', 'serviceUnavailableHelp', 'D03', 'checkAccess'), options('mindbox', 'D02')),
    frame('D09', 'Mindbox · отсутствует безопасная проверка', t('checkAccess'), t('mindboxLead'), issue('missingOperation', 'missingOperationHelp', 'D02', 'backToConnection'), options('mindbox', 'D02')),
    frame('D10', 'Mindbox · сценарий включён', t('mindboxPreset'), t('mindboxLead'), [h(S.Review, { service: 'mindbox', enabled: true })], options('mindbox', 'D04')),
  ];
};
