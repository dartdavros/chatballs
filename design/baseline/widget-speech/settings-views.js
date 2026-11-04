(function () {
  const { h, U, t, text, field, card, action, spinner, Toggle } = window.SpeechParts;
  const select = (label, value, choices, help, disabled) => field(label, value, { choices, help, disabled });
  function Check({ kind, status, onCheck }) {
    const loading = status === 'checking';
    return h('div', { className: 'sp-check' }, text('strong', kind),
      h('div', { className: 'sp-check-status', role: 'status' }, loading ? spinner() : h(U.StatusPill,
        { status: status === 'connected' ? 'healthy' : status === 'unavailable' ? 'error' : 'unchecked', label: t(status) })),
      action(kind === 'stt' ? 'checkStt' : 'checkTts', onCheck, false, loading));
  }
  function Connection({ id, go }) {
    const fresh = ['S01', 'S07'].includes(id);
    const stt = id === 'S03' ? 'checking' : ['S04', 'S06', 'S17'].includes(id) ? 'connected' : 'unchecked';
    const tts = id === 'S17' ? 'checking' : id === 'S04' ? 'connected' : id === 'S06' ? 'unavailable' : 'unchecked';
    return h('div', { className: 'administration-card server-form sp-connection' }, text('p', 'connectHelp'),
      h('div', { className: 'administration-fields sp-connection-fields' }, field('connectionName', t('connectionValue')),
        field('folder', fresh ? '' : t('folderExample')),
        h('div', { className: 'administration-field-wide sp-connection-secret' },
          field('secret', fresh ? '' : '••••••••••••', { type: 'password', help: 'secretHelp', error: id === 'S07' && 'required' }))),
      text('p', 'privacy', { className: 'settings-section-note' }),
      h('div', { className: 'sp-checks' }, h(Check, { kind: 'stt', status: stt, onCheck: () => go('S03') }),
        h(Check, { kind: 'tts', status: tts, onCheck: () => go('S17') })),
      id === 'S05' && text('div', 'keyError', { className: 'administration-message error', role: 'alert' }),
      id === 'S06' && text('div', 'capabilityError', { className: 'administration-message error', role: 'alert' }),
      h('div', { className: 'administration-actions' }, action(fresh ? 'connect' : 'save', () => fresh && go('S02'), true)));
  }
  function Model({ id }) {
    const defaults = id === 'S09', broken = id === 'S10';
    return card('modelCard', text('p', 'modelLead'),
      h('div', { className: 'agent-side-fields sp-form' },
        select('textProvider', 'textProviderValue', ['textProviderValue']), field('textModel', t('textModelValue')),
        select('sttProvider', defaults ? 'inherit' : 'connectionValue', ['inherit', 'connectionValue'], defaults ? 'inheritHelp' : undefined),
        field('sttModel', t('modelDefault')), select('speechLanguage', 'organizationLanguage', ['organizationLanguage']),
        broken && text('div', 'explicitError', { className: 'integration-form-error', role: 'alert' }),
        select('ttsProvider', defaults ? 'disabled' : 'connectionValue', ['disabled', 'connectionValue']),
        field('ttsModel', defaults ? '' : t('modelDefault'), { disabled: defaults }),
        select('voice', 'voiceValue', ['voiceValue'], 'voiceHelp', defaults),
        text('p', 'privacy', { className: 'settings-section-note' })));
  }
  function Web({ id }) {
    const voice = ['S12', 'S15'].includes(id), off = id === 'S13', noAgent = id === 'S15';
    return h('div', { className: 'sp-form' },
      field('title', t('siteName')), field('allowedDomains', 'https://obed.ru'),
      select('routeAgent', noAgent ? 'operators' : 'agentName', ['agentName', 'operators']),
      select('group', 'assignmentText', ['assignmentText']),
      select('microphone', off ? 'off' : voice ? 'voiceMode' : 'dictationMode', noAgent ? ['off', 'voiceMode'] : ['off', 'voiceMode', 'dictationMode'], 'modeHelp'),
      h('div', { className: 'server-two-fields' },
        field('maxSize', id === 'S14' ? '0' : '10', { type: 'number', help: 'sizeHelp', error: id === 'S14' && 'limitsError' }),
        field('maxDuration', id === 'S14' ? '-1' : '60', { type: 'number', help: 'durationHelp', disabled: voice || off })),
      h(Toggle, { label: 'listenWeb', help: 'listenHelp', checked: !voice && !off && !noAgent, disabled: noAgent }),
      text('p', noAgent ? 'noAgent' : 'defaultsHelp', { className: 'settings-section-note' }),
      text('p', 'privacy', { className: 'settings-section-note' }),
      h('div', { className: 'portal-settings-actions' }, action('save', () => {}, true, id === 'S14')));
  }
  function Consent() {
    return h('div', { className: 'cb-widget', style: { '--cb-accent': '#0f9b8e' } }, h(window.SpeechProduct.PreChatForm, {
      config: { autonomous: true, preChat: { enabled: true, title: t('consentTitle'), fields: [{ key: 'name', required: true }] },
        consent: { text: `<p>${t('consentText')}</p>`, version: '1' } },
      accent: '#0f9b8e', title: t('header'), siteValues: {}, starting: false,
      onAccept: async () => window.SpeechGo?.('D01'),
    }));
  }
  window.SpeechSettingsView = ({ id, go }) => id === 'S16' ? h(Consent)
    : ['S08', 'S09', 'S10'].includes(id) ? h(Model, { id })
      : /^S1[1-5]$/.test(id) ? h(Web, { id }) : h(Connection, { id, go });
})();
