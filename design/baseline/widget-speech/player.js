// VoiceMessage's existing player/wave/play classes and original composer.css.
// This controlled design view illustrates states without an Audio object or URL.
(function () {
  const { h, t, spinner } = window.SpeechParts;
  const icon = name => h(window.SpeechProduct.SpeechIcon, { name, size: 14 });
  function Player({ state, onChange, seed = 1 }) {
    const wave = window.React.useRef(null);
    const [bars, setBars] = window.React.useState(32);
    window.React.useLayoutEffect(() => {
      const measure = () => setBars(Math.min(32, Math.max(8, Math.floor((wave.current.clientWidth + 2) / 5))));
      measure(); const observer = new ResizeObserver(measure); observer.observe(wave.current);
      return () => observer.disconnect();
    }, []);
    const error = ['voiceUnavailable', 'languageUnavailable', 'ttsFailure', 'playbackFailure'].includes(state);
    const loading = state === 'loading', active = ['playing', 'paused'].includes(state);
    const replay = ['ended', 'stopped'].includes(state);
    const label = loading ? 'loadingAudio' : state === 'playing' ? 'pause' : state === 'paused' ? 'resume'
      : replay ? 'replay' : error ? 'retry' : 'listen';
    const primary = () => onChange(state === 'playing' ? 'paused' : state === 'paused' ? 'playing' : 'loading');
    const caption = error ? state : loading ? 'loadingAudio' : active ? (state === 'playing' ? 'playing' : 'paused')
      : replay ? state : 'listen';
    return h('div', { className: 'voice-message sp-player', 'data-player-state': state },
      h('div', { className: 'voice-message-player' },
        h('button', { type: 'button', className: 'voice-message-play', onClick: primary, disabled: loading,
          'aria-label': t(label), title: t(label) }, loading ? spinner() : icon(error || replay ? 'refresh' : state === 'playing' ? 'pause' : 'play', 14)),
        h('span', { ref: wave, className: 'voice-message-wave', 'aria-hidden': true },
          ...window.SpeechProduct.voiceWaveHeights(seed, bars).map((height, index) => h('i', {
            key: index, style: { height }, className: active && index < 8 ? 'is-played' : '',
          }))),
        h('em', null, active ? '0:12' : replay ? '0:48' : '—:—')),
      h('div', { className: `sp-player-status ${error ? 'voice-message-error' : ''}`, role: 'status', 'aria-live': 'polite' },
        h('span', null, t(caption))));
  }
  window.SpeechPlayer = Player;
})();
