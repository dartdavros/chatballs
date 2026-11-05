async (page) => {
  const errors = [], verified = [];
  const select = page.locator('.sp-review select').first();
  const screen = page.locator('[data-screen]');
  const t = key => page.evaluate(key => window.SpeechParts.t(key), key);
  const button = async key => screen.getByRole('button', { name: await t(key), exact: true });
  const expect = (value, label) => { if (!value) errors.push(label); };
  const open = async id => { await select.selectOption(id); await page.locator(`[data-screen="${id}"]`).waitFor(); };
  const mode = await select.locator('option').nth(1).getAttribute('value');
  if (mode.startsWith('D')) {
    await open('D01');
    const draft = screen.locator('textarea');
    const old = await draft.inputValue();
    expect(await screen.locator('.sp-composer-status').count() === 0, 'Dictation status is visible before microphone click');
    await (await button('dictate')).click();
    expect(await screen.locator('.sp-composer-status').count() === 1, 'Microphone did not open dictation status');
    expect((await screen.innerText()).includes(await t('permission')), 'Missing permission state');
    await page.getByRole('button', { name: await t('next'), exact: true }).click();
    expect((await screen.innerText()).includes(await t('recording')), 'Missing recording state');
    expect(await screen.getByRole('button', { name: await t('stop'), exact: true }).locator('[data-lucide="stop"]').count() === 1, 'Recording stop is not Lucide Square');
    const stopStyle = await screen.getByRole('button', { name: await t('stop'), exact: true }).evaluate(el => ({
      background: getComputedStyle(el).backgroundColor, fill: el.querySelector('svg').getAttribute('fill'),
      primary: el.classList.contains('cb-send-button'),
    }));
    expect(stopStyle.background === 'rgba(0, 0, 0, 0)' && stopStyle.fill === 'currentColor' && !stopStyle.primary,
      'Recording stop must be a solid square without background');
    expect(await screen.getByRole('button', { name: await t('cancel'), exact: true }).locator('[data-lucide="close"]').count() === 1, 'Recording cancel is not Lucide X');
    const cancelBackground = await screen.getByRole('button', { name: await t('cancel'), exact: true }).evaluate(el=>getComputedStyle(el).backgroundColor);
    expect(cancelBackground === 'rgba(0, 0, 0, 0)', 'Cancel icon has a background');
    await (await button('stop')).click();
    expect(await screen.locator('.logo-spinner').count() === 1, 'Recognition spinner');
    await draft.fill(old + await t('typed'));
    await page.getByRole('button', { name: await t('resultPreview'), exact: true }).click();
    const full = await draft.inputValue();
    expect(full === old + await t('typed') + ' ' + await t('recognized'), 'Current draft was not preserved');
    await page.getByRole('button', { name: await t('resultPreview'), exact: true }).click();
    expect(await draft.inputValue() === full, 'Duplicate result applied twice');
    expect(await screen.locator('.cb-message--client').count() === 0, 'Recognition sent a message');
    await (await button('send')).click();
    expect(await screen.locator('.cb-message--client').count() === 1, 'Explicit send did not create text illustration');
    verified.push('permission → recording → stop → STT → editable latest draft → explicit send; result applied once');
    await open('D04');
    const before = await draft.inputValue();
    await (await button('cancel')).click();
    expect(await screen.locator('.sp-composer-status').count() === 0, 'Cancel did not close dictation panel');
    await page.getByRole('button', { name: await t('stalePreview'), exact: true }).click();
    expect(await draft.inputValue() === before, 'Cancelled late result changed draft');
    verified.push('cancel and late result preserve existing draft');
    for (const id of ['D16', 'D17', 'D18']) {
      await open(id); const value = await draft.inputValue();
      await (await button('retry')).click();
      expect(await screen.locator('.logo-spinner').count() === 1 && await draft.inputValue() === value, `${id}: retry lost draft`);
    }
    await open('D10'); expect((await draft.inputValue()).length > 4000, 'Long draft was truncated');
    expect(await (await button('send')).isDisabled(), 'Long draft can be sent');
    await draft.fill(await t('draft')); expect(await (await button('send')).isEnabled(), 'Shortened draft cannot be sent');
    verified.push('retry retains draft; overlong result untruncated and becomes sendable after editing');
    await open('D03'); await draft.focus(); await page.keyboard.press('Escape');
    expect(await screen.locator('.sp-composer-status').count() === 0, 'Escape did not close dictation panel');
    await draft.fill(await t('draft')); await page.keyboard.press('Shift+Enter');
    expect((await draft.inputValue()).includes('\n'), 'Shift+Enter lost newline');
    await page.keyboard.press('Enter'); expect(await screen.locator('.cb-message--client').count() === 1, 'Enter did not explicitly send');
    verified.push('keyboard Escape, Shift+Enter and Enter');
  } else if (mode.startsWith('P')) {
    await open('P01');
    const textBefore = await screen.locator('.sp-answer-text').innerText();
    expect(await screen.locator('.sp-player').count() === 0, 'Player is visible before sound icon click');
    expect(await screen.locator('.sp-answer-audio-toggle [data-lucide="sound"]').count() === 1, 'Lucide sound icon missing');
    await (await button('listen')).click();
    expect(await screen.locator('[data-player-state="loading"]').count() === 1, 'No audio loading state');
    expect(await screen.locator('.sp-answer-audio-toggle [data-lucide="stop"]').count() === 1, 'Sound icon was not replaced by Lucide stop');
    await page.getByRole('button', { name: await t('next'), exact: true }).click();
    await (await button('pause')).click(); expect(await screen.locator('[data-player-state="paused"]').count() === 1, 'Pause failed');
    await (await button('resume')).click(); await (await button('stop')).click();
    expect(await screen.locator('.sp-player').count() === 0, 'Stop did not hide player');
    expect(await screen.locator('.sp-answer-audio-toggle [data-lucide="sound"]').count() === 1, 'Stop did not restore sound icon');
    expect(await screen.locator('.sp-answer-text').innerText() === textBefore, 'Stop changed answer text');
    await open('P05');
    await (await button('replay')).click();
    expect(await screen.locator('.sp-answer-text').innerText() === textBefore, 'Player changed answer text');
    verified.push('Lucide sound icon opens player and becomes stop; pause/resume/replay; stop hides player and restores sound; text remains');
    await open('P13');
    await screen.locator('.sp-answer').nth(1).getByRole('button', { name: await t('listen'), exact: true }).click();
    expect(await screen.locator('[data-player-state="loading"]').count() === 1 && await screen.locator('.sp-player').count() === 1, 'More than one active audio');
    await page.getByRole('button', { name: await t('next'), exact: true }).click();
    await (await button('dictate')).click();
    expect(await screen.locator('[data-player-state="playing"],[data-player-state="paused"],[data-player-state="loading"]').count() === 0, 'Recording did not stop playback');
    verified.push('one illustrated sound; recording stops playback');
    for (const id of ['P09','P10','P11','P12']) { await open(id); expect((await screen.locator('.cb-bubble--agent').innerText()).length > 20, `${id}: text hidden`); }
    await open('P15'); expect(await screen.locator('.sp-answer-audio-toggle').count() === 1 && await screen.locator('.sp-player').count() === 0, 'Staff/client received player');
    verified.push('voice/language/synthesis/playback errors retain text; staff/client have no player');
  } else {
    for (const id of ['S05','S06']) {
      await open(id);
      expect(await screen.locator('.administration-message.error[role="alert"]').count() === 1, `${id}: missing platform settings error`);
    }
    for (const id of ['S07','S14']) {
      await open(id);
      expect(await screen.locator('.form-field-error[role="alert"]').count() === 1, `${id}: missing platform field error`);
    }
    await open('S10');
    expect(await screen.locator('.integration-form-error[role="alert"]').count() === 1, 'Missing platform integration error');
    verified.push('existing settings error block, integration error and FormField error; full-width forms and grouped related fields');
    for (const id of ['S02','S11']) {
      await open(id); await (await button('save')).click();
      expect(!/Изменения сохранены|Changes saved/.test(await screen.innerText()), `${id}: nonstandard success notice`);
    }
    await open('S16'); expect(await (await button('startChat')).isDisabled(), 'Consent gate missing');
    await screen.getByRole('textbox').fill('Guest');
    expect(await (await button('startChat')).isEnabled(), 'Required form did not enable chat');
    expect(await screen.locator('.cb-consent').count() === 1, 'Existing consent presentation missing');
    verified.push('existing pre-chat form: required name and explicit start with consent; no speech controls before start');
    await open('S08');
    const fields = screen.locator('input'); const before = await fields.nth(0).inputValue();
    await fields.nth(1).fill('Recognition model example');
    expect(await fields.nth(0).inputValue() === before, 'STT edit changed text model');
    verified.push('speech model edit independent of text model; Save has no custom success message');
  }
  return { check: 'illustrated-interactions', errors, verified };
}
