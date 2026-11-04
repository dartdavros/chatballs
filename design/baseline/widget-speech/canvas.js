(function () {
  const { h, U, t, text, link } = window.SpeechParts;
  function Canvas({ section }) {
    const query = new URLSearchParams(location.search);
    const [language, setLanguage] = window.React.useState(query.get('lang') || 'ru');
    const [theme, setTheme] = window.React.useState(query.get('theme') || 'light');
    const [width, setWidth] = window.React.useState(Number(query.get('width')) || (section === 'settings' ? 1440 : 390));
    const [accent, setAccent] = window.React.useState('#0f9b8e');
    const frames = window.SpeechFrames.filter(f => f.kind === section);
    const [selected, setSelected] = window.React.useState(query.get('frame') || frames[0].id);
    window.SpeechLanguage = language;
    window.SpeechProduct.setCurrentLanguage(language);
    window.SpeechGo = id => setSelected(id);
    window.React.useLayoutEffect(() => U.applyAppearance(theme === 'dark' ? 'DARK' : 'LIGHT', accent), [theme, accent]);
    const select = (key, value, change, options) => h('label', null, t(key), h('select', {
      'aria-label': t(key), value, onChange: e => change(e.target.value),
    }, ...options.map(([value, label]) => h('option', { key: value, value }, label))));
    const shown = selected === 'all' ? frames : window.SpeechFrames.filter(f => f.id === selected);
    return h(U.ConfigProvider, { theme: { algorithm: theme === 'dark' ? U.theme.darkAlgorithm : U.theme.defaultAlgorithm,
      token: { colorPrimary: accent } } }, h('div', { className: 'sp-canvas' },
      h('header', { className: 'sp-review' }, text('h1', 'canvasTitle'), text('p', 'canvasNote'),
        select('frame', selected, setSelected, [['all', t('all')], ...frames.map(f => [f.id, `${f.id} · ${t(f.title)}`])]),
        select('width', width, v => setWidth(Number(v)), [320, 390, 768, 1024, 1440].map(v => [v, String(v)])),
        select('theme', theme, setTheme, [['light', t('light')], ['dark', t('dark')]]),
        select('language', language, setLanguage, [['ru', 'Русский'], ['en', 'English']]),
        select('accent', accent, setAccent, U.ACCENT_PRESETS.map(([value,label]) => [value, window.SpeechProduct.translateExisting(label, language)])),
        section !== 'settings' && h('div', { className: 'sp-preview-actions' },
          link('next', () => window.SpeechPreviewNext?.()),
          link('resultPreview', () => window.SpeechPreviewResult?.(false)),
          link('stalePreview', () => window.SpeechPreviewResult?.(true)))),
      h('div', { className: 'sp-board' }, ...shown.map(frame => h('article', { key: `${frame.id}-${language}-${width}`, className: 'sp-frame' },
        h('div', { className: 'sp-caption' }, h('code', null, frame.id), text('strong', frame.title)),
        frame.id === 'S16' ? h('div', { className: 'sp-widget-screen', style: { width: Math.min(width, 420) }, 'data-screen': frame.id }, h(window.SpeechSettingsView, { id: frame.id }))
          : frame.kind === 'settings' ? h(window.SpeechSettingsScreen, { frame, width }, h(window.SpeechSettingsView, { id: frame.id, go: setSelected }))
            : h(window.SpeechWidget, { id: frame.id, width, accent }))))));
  }
  window.SpeechCanvas = Canvas;
})();
