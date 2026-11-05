// ChatComposer geometry and icons; dictation adds a compact status above its row.
(function () {
  const { h, t, spinner } = window.SpeechParts;
  const icon = name => h(window.SpeechProduct.SpeechIcon, { name });
  function IconButton({ name, label, onClick, disabled = false, primary = false, children }) {
    return h('button', { type: 'button', className: `wc-icon-button cb-composer-button ${primary ? 'cb-send-button' : ''} ${name === 'stop' ? 'sp-dictation-stop' : ''}`,
      'aria-label': t(label), title: t(label), disabled, onClick }, children || (name === 'stop' ? h(window.SpeechProduct.SpeechIcon, { name, size: 20 }) : icon(name)));
  }
  function Composer({ state, dispatch, onStart }) {
    const inputRef = window.React.useRef(null);
    const busy = ['recognizing', 'permission'].includes(state.phase);
    const recording = state.phase === 'recording';
    const error = ['error', 'retry', 'denied', 'unsupported', 'long'].includes(state.phase);
    const begin = () => { onStart(); dispatch({ type: 'start' }); };
    window.React.useLayoutEffect(() => {
      const input = inputRef.current;
      if (input) { input.style.height = 'auto'; input.style.height = `${Math.min(132, Math.max(37, input.scrollHeight))}px`; }
    }, [state.draft]);
    if (state.phase === 'voice') return h('footer', { className: 'cb-composer sp-legacy-composer' },
      h(IconButton, { name: 'close', label: 'cancel', onClick: () => dispatch({ type: 'cancel' }) }),
      h('strong', { className: 'sp-timer' }, '0:24'), h('span', null, t('voiceRecording')),
      h(IconButton, { name: 'arrow', label: 'sendVoice', primary: true, onClick: () => window.SpeechGo('D20') }));
    return h('footer', { className: 'cb-composer sp-composer', 'data-dictation-open': state.engaged },
      state.engaged && h('div', { className: `sp-composer-status ${error ? 'sp-error' : ''}`, role: 'status', 'aria-live': 'polite' },
        h('div', { className: 'sp-status-copy' },
          h('div', { className: 'sp-status-heading' }, busy && spinner(), recording && h('strong', { className: 'sp-timer' }, '0:24 / 1:00'),
            h('span', null, t(recording ? 'recording' : state.notice)))),
        h('div', { className: 'sp-status-actions' },
          state.phase === 'retry' && h(IconButton, { name: 'refresh', label: 'retry', onClick: () => dispatch({ type: 'retry' }) }),
          ['error', 'denied'].includes(state.phase) && h(IconButton, { name: 'mic', label: 'recordAgain', onClick: begin }),
          recording && h(IconButton, { name: 'stop', label: 'stop', onClick: () => dispatch({ type: 'stop' }) }),
          h(IconButton, { name: 'close', label: 'cancel', onClick: () => dispatch({ type: 'cancel' }) }))),
      h('div', { className: 'sp-input-row' },
        h(IconButton, { name: 'paperclip', label: 'attach', disabled: true }),
        h('textarea', { ref: inputRef, className: 'cb-composer-input',
          'aria-label': t('message'), placeholder: t('placeholder'), value: state.draft, rows: 1,
          onChange: e => dispatch({ type: 'type', value: e.target.value }),
          onKeyDown: e => { if (e.key === 'Escape' && state.engaged) dispatch({ type: 'cancel' });
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); dispatch({ type: 'send' }); } } }),
        h(IconButton, { name: 'mic', label: 'dictate', onClick: begin, disabled: busy || recording || state.phase === 'unsupported' }),
        h(IconButton, { name: 'arrow', label: 'send', primary: true, onClick: () => dispatch({ type: 'send' }),
          disabled: busy || recording || state.phase === 'long' || !state.draft.trim() })));
  }
  window.SpeechComposer = Composer;
})();
