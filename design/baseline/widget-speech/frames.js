// Semantic frame inventory; captions live outside product screens.
(function () {
  const frames = (prefix, count, kind) => Array.from({ length: count }, (_, index) => {
    const id = prefix + String(index + 1).padStart(2, '0');
    return { id, title: id.toLowerCase(), kind };
  });
  window.SpeechFrames = [...frames('S', 17, 'settings'), ...frames('D', 20, 'dictation'), ...frames('P', 15, 'playback')];
  window.SpeechDictation = {
    D01: ['idle', 'ready'], D02: ['permission', 'permission'], D03: ['recording', 'recordingHelp'],
    D04: ['recognizing', 'recognizing'], D05: ['result', 'result'], D06: ['cancelled', 'cancelled'],
    D07: ['recognizing', 'durationLimit'], D08: ['recognizing', 'sizeLimit'], D09: ['recognizing', 'recognizing'],
    D10: ['long', 'tooLong'], D11: ['error', 'emptySpeech'], D12: ['unsupported', 'unsupported'],
    D13: ['denied', 'denied'], D14: ['error', 'limitError'], D15: ['error', 'formatError'],
    D16: ['retry', 'networkError'], D17: ['retry', 'providerError'], D18: ['retry', 'timeoutError'],
    D19: ['voice', 'voiceRecording'], D20: ['sentVoice', 'ready'],
  };
  window.SpeechPlayback = {
    P01: 'idle', P02: 'loading', P03: 'playing', P04: 'paused', P05: 'ended', P06: 'stopped',
    P07: 'playing', P08: 'playing', P09: 'voiceUnavailable', P10: 'languageUnavailable',
    P11: 'ttsFailure', P12: 'playbackFailure', P13: 'playing', P14: 'stopped', P15: 'idle',
  };
})();
