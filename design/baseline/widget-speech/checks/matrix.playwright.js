async (page) => {
  const selects = page.locator('.sp-review select');
  const frames = await page.evaluate(() => window.SpeechFrames.filter(f => f.kind === (
    document.querySelector('.sp-review select option[value="S01"]') ? 'settings'
      : document.querySelector('.sp-review select option[value="D01"]') ? 'dictation' : 'playback')).map(f => f.id));
  const settings = frames[0].startsWith('S');
  const errors = [], sizes = [], captures = [];
  let measured = 0;
  for (const lang of ['ru', 'en']) {
    await selects.nth(3).selectOption(lang);
    for (const theme of ['light', 'dark']) {
      await selects.nth(2).selectOption(theme);
      for (const width of settings ? [320, 390, 768, 1024, 1440] : [320, 390, 1440]) {
        await selects.nth(1).selectOption(String(width));
        for (const id of frames) {
          await selects.nth(0).selectOption(id);
          const screen = page.locator(`[data-screen="${id}"]`);
          await screen.waitFor();
          const result = await screen.evaluate(el => {
            const box = el.getBoundingClientRect();
            const visible = [...el.querySelectorAll('button,input,textarea,select')].filter(n => n.getClientRects().length);
            const outside = visible.filter(n => {
              const rect = n.getBoundingClientRect();
              return rect.left < box.left - 1 || rect.right > box.right + 1;
            }).map(n => ({ tag: n.tagName, cls: n.className, label: n.getAttribute('aria-label') }));
            const text = el.innerText;
            const internal = /SPEC-|ADR-|DG-|Q-WIDGET|инвариант|констрейнт|scope|allowCheckoutActions|\bnull\b/.test(text);
            const composer = el.querySelector('.sp-composer')?.getBoundingClientRect();
            const player = el.querySelector('.sp-player')?.getBoundingClientRect();
            const status = el.querySelector('.sp-composer-status');
            const statusCopy = el.querySelector('.sp-status-copy');
            const pair = [...el.querySelectorAll('.sp-connection-fields > .sp-field input')].map(n => n.getBoundingClientRect());
            const secret = el.querySelector('.sp-connection-secret input')?.getBoundingClientRect();
            const fieldLayout = pair.length === 2 && secret ? {
              equal: Math.abs(pair[0].width - pair[1].width) < 1,
              aligned: Math.abs(pair[0].y - pair[1].y) < 1,
              full: Math.abs(secret.left - pair[0].left) < 1 && Math.abs(secret.right - pair[1].right) < 1,
            } : null;
            const webForm = el.querySelector('.portal-settings-card .sp-form');
            const webFull = !webForm || [...webForm.querySelectorAll(':scope > .sp-field input,:scope > .sp-field .ant-select')]
              .every(n => Math.abs(n.getBoundingClientRect().width - webForm.getBoundingClientRect().width) < 2);
            return { width: el.clientWidth, scrollWidth: el.scrollWidth, outside, internal, webFull,
              composerHeight: composer?.height, playerHeight: player?.height,
              statusHeight: status?.getBoundingClientRect().height, fieldLayout,
              statusFits: !status || statusCopy.getBoundingClientRect().height <= status.clientHeight,
              iframe: el.querySelectorAll('.prepared-message-frame').length,
              spinner: el.querySelectorAll('.logo-spinner').length };
          });
          measured++;
          if (result.scrollWidth > result.width + 1 || result.outside.length || result.internal) errors.push({ id, lang, theme, width, ...result });
          if (!result.statusFits) errors.push({ id, lang, width, error: 'Compact dictation status overflows' });
          if (!result.webFull) errors.push({ id, lang, width, error: 'WEB fields do not fill the platform form' });
          if (result.fieldLayout && !Object.values(result.fieldLayout).every(Boolean)) errors.push({ id, lang, width, error: 'Connection fields are not 50/50 plus full-width key', ...result.fieldLayout });
          if (['D01','D20'].includes(id) && result.statusHeight) errors.push({ id, error: 'Idle dictation status must be hidden' });
          if (['P01','P06','P14','P15'].includes(id) && result.playerHeight) errors.push({ id, error: 'Closed playback must show only sound icon' });
          sizes.push({ id, lang, theme, width, status: result.statusHeight, player: result.playerHeight });
          if (id === 'P08' && result.iframe !== 1) errors.push({ id, error: 'Formatted answer is missing' });
          if (['D04','D07','D08','D09','P02','S03','S17'].includes(id) && !result.spinner) errors.push({ id, error: 'Shared spinner is missing' });
          if ((lang === 'ru' && theme === 'light' && width === 1440)
            || (lang === 'en' && theme === 'dark' && width === 320)) {
            const filename = `design/baseline/widget-speech/verification/${id}-${lang}-${theme}-${width}.png`;
            await screen.screenshot({ path: filename, animations: 'disabled' });
            captures.push(filename);
            const scrolled = await screen.evaluate(el => {
              const nodes = [...el.querySelectorAll('.settings-content,.portal-settings-content,.sp-agent,.cb-body')]
                .filter(n => n.scrollHeight > n.clientHeight + 2);
              nodes.forEach(n => { n.scrollTop = n.scrollHeight; });
              return nodes.length;
            });
            if (scrolled) {
              await screen.screenshot({ path: filename.replace('.png','-bottom.png'), animations: 'disabled' });
              captures.push(filename.replace('.png','-bottom.png'));
              await screen.evaluate(el => el.querySelectorAll('.settings-content,.portal-settings-content,.sp-agent,.cb-body').forEach(n => { n.scrollTop = 0; }));
            }
          }
        }
      }
    }
  }
  for (const lang of ['ru','en']) for (const theme of ['light','dark']) for (const width of settings ? [] : [320,390,1440]) {
    const matching = sizes.filter(s => s.lang === lang && s.theme === theme && s.width === width);
    const statuses = matching.map(s => s.status).filter(Boolean);
    const players = matching.map(s => s.player).filter(Boolean);
    if (statuses.length && Math.max(...statuses) - Math.min(...statuses) > 1) errors.push({ lang, theme, width, error: 'Active dictation status geometry changes', statuses });
    if (players.length && Math.max(...players) - Math.min(...players) > 1) errors.push({ lang, theme, width, error: 'Player geometry changes', players });
  }
  return { check: 'responsive-state-matrix', frames: frames.length, measured, errors, captures: captures.length,
    verified: 'both languages/themes, 320/390/768/1024/1440 settings, 320/390/420 widget, shared spinner, formatted answer, stable geometry, no internal codes' };
}
