// Illustrative scheduling in the design document, never a job scheduler.
(function () {
  const defaults = () => ({ manual: true, ai: false, internal: false, external: false, schedule: false, api: false, nested: false,
    aiMode: 'forbidden', agent: 'support', internalEvent: 'transfer', externalEvent: 'deal', delivery: 'webhook', poll: '5',
    repeat: 'weekdays', time: '09:00', date: '', interval: '60', zone: 'Europe/Moscow', missed: 'once', gap: 'next', fold: 'first',
    apiAccess: 'corporate', delegate: false, owner: '' });
  const automatic = value => ['internal','external','schedule','api'].some(key => value[key]);
  const errors = value => {
    const result = [];
    if (!['manual','ai','internal','external','schedule','api','nested'].some(k => value[k])) result.push('launchRequired');
    if (value.ai && value.aiMode === 'forbidden') result.push('aiRequired');
    if (automatic(value) && (!value.owner || !value.delegate)) result.push('delegationMissing');
    if (value.schedule && (!/^\d{2}:\d{2}$/.test(value.time) || value.repeat === 'once' && !value.date || value.repeat === 'interval' && !(Number(value.interval) > 0))) result.push('scheduleRequired');
    return result;
  };
  function preview(value) {
    const formatter = new Intl.DateTimeFormat(document.documentElement.lang || navigator.language, { timeZone: value.zone, year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' });
    const dates = [], now = new Date(), local = formatter.formatToParts(now), get = type => local.find(p => p.type === type)?.value;
    const start = new Date(Date.UTC(Number(get('year')), Number(get('month')) - 1, Number(get('day')), 12));
    if (value.repeat === 'once' && value.date) return [[value.date, value.time, value.zone]];
    if (value.repeat === 'interval') return Array.from({ length: 3 }, (_, i) => {
      const date = new Date(now.getTime() + Number(value.interval || 60) * 60000 * (i + 1));
      return [formatter.format(date), new Intl.DateTimeFormat(document.documentElement.lang || navigator.language, { timeZone: value.zone, hour: '2-digit', minute: '2-digit' }).format(date), value.zone];
    });
    for (let n = 1; dates.length < 3 && n < 9; n++) {
      const date = new Date(start.getTime() + n * 86400000);
      if (value.repeat === 'weekdays' && [0,6].includes(date.getUTCDay())) continue;
      dates.push([formatter.format(date), value.time, value.zone]);
    }
    return dates;
  }
  window.LaunchModel = { defaults, automatic, errors, preview };
})();
