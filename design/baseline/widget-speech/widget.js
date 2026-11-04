(function () {
  const { h, t, text, icon } = window.SpeechParts;
  const Product = window.SpeechProduct;
  function Answer({ id, index, active, setActive, initialState, accent }) {
    const [state, setState] = window.React.useState(initialState);
    const [open, setOpen] = window.React.useState(!['idle', 'stopped'].includes(initialState));
    const current = active === index ? state : ['playing', 'paused', 'loading'].includes(state) ? 'stopped' : state;
    const update = next => { setActive(['loading', 'playing', 'paused'].includes(next) ? index : null); setState(next); };
    const toggle = () => {
      if (open) { setState('stopped'); setOpen(false); if (active === index) setActive(null); }
      else { setOpen(true); update('loading'); }
    };
    window.React.useEffect(() => {
      if (active !== index && ['playing', 'paused', 'loading'].includes(state)) { setState('stopped'); setOpen(false); }
    }, [active, index, state]);
    // Canvas controls advance an illustration; no synthesis or audio element is created.
    window.React.useEffect(() => {
      const advance = () => { if (current === 'loading') update('playing'); };
      window.addEventListener('speech-preview-audio', advance);
      return () => window.removeEventListener('speech-preview-audio', advance);
    }, [current]);
    const content = index === 1 ? t('secondAnswer') : id === 'P07' ? t('answerLong').repeat(8) : t('answer');
    const formatted = id === 'P08' ? { formatVersion: 1, presentation: { formatVersion: 1, css: '', isolation: 'sandboxed-iframe', sandbox: '',
      srcDoc: `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;padding:8px;font:14px/1.6 system-ui;color:#262626}h3{font-size:16px;margin:0 0 8px}ul{padding-left:20px}p{margin-bottom:0}</style></head><body><h3>${t('formattedTitle')}</h3><ul><li>${t('formattedItem')}</li></ul><p><strong>${t('formattedNote')}</strong></p></body></html>` } } : undefined;
    return h('section', { className: 'sp-answer' }, h(Product.Bubble, { author: 'ai', authorName: t('header'), accent,
      text: h(window.React.Fragment, null,
        h('div', { className: 'sp-answer-text' }, formatted
          ? h(Product.PreparedMessage, { content: { ...formatted, text: content }, title: t('formattedTitle') }) : content),
        h('div', { className: 'sp-answer-audio', 'data-audio-open': open },
          open && h(window.SpeechPlayer, { state: current, onChange: update, seed: index + 1 }),
          h('button', { type: 'button', className: 'wc-icon-button cb-composer-button sp-answer-audio-toggle',
            onClick: toggle, 'aria-label': t(open ? 'stop' : 'listen'), title: t(open ? 'stop' : 'listen'),
            'aria-expanded': open }, h(Product.SpeechIcon, { name: open ? 'stop' : 'sound', size: 16 })))) }));
  }
  function Widget({ id, width, accent }) {
    const playback = id.startsWith('P');
    const [state, dispatch] = window.React.useReducer(window.SpeechDraft.reduce, id === 'P14' ? 'D03' : id, window.SpeechDraft.initial);
    const [active, setActive] = window.React.useState(playback && !['P01', 'P05', 'P06', 'P09', 'P10', 'P11', 'P12', 'P14', 'P15'].includes(id) ? 0 : null);
    window.SpeechPreviewResult = stale => dispatch({ type: 'result', attempt: state.attempt - (stale ? 1 : 0) });
    window.SpeechPreviewNext = () => {
      if (state.phase === 'permission') dispatch({ type: 'permit' });
      else if (state.phase === 'recognizing') dispatch({ type: 'result', attempt: state.attempt });
      else window.dispatchEvent(new Event('speech-preview-audio'));
    };
    return h('div', { className: 'sp-widget-screen', style: { width: Math.min(width, 420), '--cb-accent': accent }, 'data-screen': id },
      h('div', { className: 'cb-widget' }, h('header', { className: 'cb-header' },
        h(Product.BotAvatar, { accent, size: 34 }), text('strong', 'headerLong', { className: 'cb-header-title', title: t('headerLong') }),
        h('button', { className: 'cb-header-button', 'aria-label': t('close') }, icon('close'))),
      h('main', { className: 'cb-body' },
        !playback && h(Product.Bubble, { author: 'ai', authorName: t('header'), text: t('greeting'), accent }),
        playback && h(Answer, { id, index: 0, active, setActive, initialState: window.SpeechPlayback[id], accent }),
        id === 'P13' && h(Answer, { id, index: 1, active, setActive, initialState: 'idle', accent }),
        id === 'P15' && h(Product.Bubble, { author: 'operator', authorName: t('operatorName'), text: t('operatorAnswer'), accent }),
        id === 'P15' && h(Product.Bubble, { author: 'client', text: t('draft'), accent }),
        id === 'D20' && h(Product.Bubble, { author: 'client', text: h(window.SpeechVoicePreview), accent }),
        ...state.sent.map((value, index) => h(Product.Bubble, { key: index, author: 'client', text: value, accent }))),
      h(window.SpeechComposer, { state, dispatch, onStart: () => setActive(null) }),
      h('div', { className: 'cb-brand' }, h('span', null, 'Chatballs'))));
  }
  window.SpeechWidget = Widget;
})();
