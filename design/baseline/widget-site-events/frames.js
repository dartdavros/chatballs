window.EventFrames = [
  ...['S01','S02','S03','S04','S05','S06','S07'].map(id => ({ id, kind: 'settings' })),
  ...[
    ['V01','invite','noteInvite'], ['V02','consent','noteConsent'], ['V03','form','noteForm'],
    ['V04','stale','noteStale'], ['V05','current','noteCurrent'], ['V06','loading','noteAnswer'],
    ['V07','answer','noteAnswer'], ['V08','unavailable','noteFailure'], ['V09','failed','noteFailure'],
    ['V10','ordinary','notePriority'], ['V11','operator','noteOperator'], ['V12','dismissed','noteDismiss'],
    ['V13','expired','noteExpiry'], ['V14','reloaded','noteReload'], ['V15','invite','notePending'],
    ['V16','late','noteExpiry'], ['V17','closed','noteClosed'],
  ].map(([id, phase, note]) => ({ id, kind: 'visitor', phase, note })),
];
