// Design-document state only; not a site-event implementation or backend substitute.
(function () {
  const initial = phase => ({ phase:phase==='current'?'loading':phase, open: !['invite','dismissed','expired','reloaded','closed','current'].includes(phase),
    pending: ['invite','consent','stale','form','loading','current'].includes(phase), sent: [], draft: '', elapsed: phase==='late' });
  function reduce(s, a) {
    switch(a.type) {
      case 'open': return {...s,open:!s.open,phase:s.open?s.phase:(s.phase==='invite'?'consent':s.phase)};
      case 'accept': return {...s,open:true,phase:'consent'};
      case 'dismiss': return {...s,phase:'dismissed',pending:false,open:false};
      case 'expire': return {...s,pending:false,elapsed:true,phase:s.open?'late':'expired'};
      case 'consent': return {...s,phase:s.elapsed?'empty':'loading',pending:!s.elapsed};
      case 'complete': return s.phase==='loading' && s.pending ? {...s,phase:'answer',pending:false} : s;
      case 'takeover': return {...s,phase:'operator',pending:false,open:true};
      case 'draft': return {...s,draft:a.value};
      case 'send': return s.draft.trim() ? {...s,phase:'ordinary',pending:false,sent:[...s.sent,s.draft],draft:''} : s;
      case 'another': return s; // First event owns the waiting slot; dismissed/expired rules stay suppressed.
      default: return s;
    }
  }
  window.EventPreviewModel = {initial,reduce};
})();
