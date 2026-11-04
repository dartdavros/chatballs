// Static illustration of VoiceMessage.tsx; uses its original wave generator.
// No Audio is constructed and no URL is requested in this design document.
(function () {
  const { h, t } = window.SpeechParts;
  window.SpeechVoicePreview = function () {
    const [playing, setPlaying] = window.React.useState(false);
    return h('div', { className: 'sp-legacy-player' }, h('button', { type: 'button',
      'aria-label': t(playing ? 'pause' : 'listen'), onClick: () => setPlaying(!playing) },
      h(window.SpeechProduct.SpeechIcon, { name: playing ? 'pause' : 'play', size: 13 })),
      h('span', { className: 'sp-legacy-wave', 'aria-hidden': true },
        ...window.SpeechProduct.voiceWaveHeights(1).map((height, key) => h('i', { key, style: { height } }))),
      h('span', null, '0:24'));
  };
})();
