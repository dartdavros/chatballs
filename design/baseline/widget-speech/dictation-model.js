// A design-document state machine. It does not use microphone, audio or APIs.
(function () {
  const { t } = window.SpeechParts;
  function initial(id) {
    const [phase, notice] = window.SpeechDictation[id] || ['idle', 'ready'];
    let draft = t('draft');
    if (id === 'D09') draft += t('typed');
    if (id === 'D05') draft += ' ' + t('recognized');
    if (id === 'D10') draft += ' ' + t('answerLong').repeat(20);
    return { phase, notice, draft, engaged: !['idle', 'sentVoice', 'voice'].includes(phase), attempt: 1, applied: false, sent: [] };
  }
  function reduce(state, event) {
    switch (event.type) {
      case 'type': return { ...state, draft: event.value,
        ...(state.phase === 'long' && event.value.length <= 4000 ? { phase: 'result', notice: 'result' } : {}) };
      case 'start': return { ...state, engaged: true, phase: 'permission', notice: 'permission', attempt: state.attempt + 1, applied: false };
      case 'permit': return { ...state, phase: 'recording', notice: 'recordingHelp' };
      case 'stop': return { ...state, phase: 'recognizing', notice: 'recognizing' };
      case 'cancel': return { ...state, phase: 'cancelled', notice: 'cancelled',
        engaged: false, attempt: state.attempt + 1 };
      case 'retry': return { ...state, phase: 'recognizing', notice: 'recognizing', attempt: state.attempt + 1, applied: false };
      case 'result':
        if (state.phase !== 'recognizing' || state.applied || event.attempt !== state.attempt) return state;
        return { ...state, phase: 'result', notice: 'result', applied: true,
          draft: [state.draft.trimEnd(), t('recognized')].filter(Boolean).join(' ') };
      case 'send':
        if (!state.draft.trim() || state.phase === 'long' || ['recognizing', 'recording', 'permission'].includes(state.phase)) return state;
        return { ...state, sent: [...state.sent, state.draft], draft: '', engaged: false, phase: 'idle', notice: 'ready' };
      default: return state;
    }
  }
  window.SpeechDraft = { initial, reduce };
})();
