import assert from 'node:assert/strict';

// Read actual layout/styles only; no API, clipboard or UI-state replacement.
export function qualityGeometry() {
  const frame = document.querySelector('.ea-screen'), footer = frame.querySelector('footer.external-save-footer');
  const actions = footer?.querySelector('[data-save-actions]'), template = frame.querySelector('[data-template-grants]');
  const saveLabel = footer?.querySelector('[data-save-label]')?.textContent.trim();
  const walker = document.createTreeWalker(frame, NodeFilter.SHOW_TEXT); let node, savingTextCount = 0;
  while ((node = walker.nextNode())) if (saveLabel && node.textContent.trim() === saveLabel) savingTextCount += 1;
  const error = frame.querySelector('[data-load-error-alert]'), alert = error?.querySelector('.service-alert.is-error');
  const alertStyle = alert && getComputedStyle(alert), retry = error?.nextElementSibling;
  const feature = frame.querySelector('.external-feature-state'), featureStyle = feature && getComputedStyle(feature);
  const cells = [...frame.querySelectorAll('.ui-switch-cell')], headers = [...frame.querySelectorAll('.ui-switch-column')];
  const directGap = (before, after) => before && after ? after.getBoundingClientRect().top - before.getBoundingClientRect().bottom : null;
  return {
    saveFeedbackCount: frame.querySelectorAll('[data-save-feedback]').length,
    footer: footer ? { tag: footer.tagName, state: footer.dataset.saveState, gap: directGap(template, footer),
      height: footer.getBoundingClientRect().height, actionsHeight: actions?.getBoundingClientRect().height,
      actionsGap: actions ? actions.getBoundingClientRect().top - (actions.previousElementSibling?.getBoundingClientRect().bottom ?? footer.getBoundingClientRect().top) : null,
      spinnerInButton: footer.querySelectorAll('button .logo-spinner').length, frameSpinnerCount: frame.querySelectorAll('.logo-spinner').length,
      waitingRows: footer.querySelectorAll('.service-oauth-waiting').length, frameWaitingRows: frame.querySelectorAll('.service-oauth-waiting').length,
      savingTextCount, buttonBusy: footer.getAttribute('aria-busy'),
      actionsPosition: actions && getComputedStyle(actions).position, actionsBackground: actions && getComputedStyle(actions).backgroundColor,
    } : null,
    loadError: alert ? { icons: alert.querySelectorAll('svg').length, background: alertStyle.backgroundColor,
      borders: ['Top', 'Right', 'Bottom', 'Left'].map(side => ({ width: parseFloat(alertStyle[`border${side}Width`]), style: alertStyle[`border${side}Style`] })),
      retryGap: directGap(error, retry), display: getComputedStyle(error.parentElement).display,
    } : null,
    feature: feature ? { display: featureStyle.display, gap: parseFloat(featureStyle.rowGap) } : null,
    tableHeaders: headers.map(cell => getComputedStyle(cell).textAlign),
    tableCells: cells.map(cell => { const button = cell.querySelector(':scope > .ui-switch'); return {
      align: getComputedStyle(cell).textAlign, inset: button ? cell.getBoundingClientRect().right - button.getBoundingClientRect().right : null,
    }; }),
    links: [...frame.querySelectorAll('.link:not(.is-strong):not(.is-mono)')].map(link => parseFloat(getComputedStyle(link).fontSize)),
    reviewFieldGaps: [...frame.querySelectorAll('.administration-message + .administration-fields')].map(fields => directGap(fields.previousElementSibling, fields)),
    policyGaps: [...frame.querySelectorAll('[data-policy-agent]')].map(target => directGap(target, target.nextElementSibling)).filter(gap => gap !== null),
  };
}

export function validateQualityGeometry(g, c) {
  if (c.group !== 'settings') return;
  assert.equal(g.saveFeedbackCount, 0, `${c.id}: no obsolete save-feedback placeholder`);
  if (!['S31', 'S32', 'S36'].includes(c.id)) {
    assert(g.footer, `${c.id}: compact semantic footer`); assert.equal(g.footer.tag, 'FOOTER');
    assert(Math.abs(g.footer.gap - 18) <= 1, `${c.id}: footer gap ${g.footer.gap}`);
    assert(g.footer.actionsHeight >= 33 && g.footer.actionsHeight <= 70, `${c.id}: compact action row ${g.footer.actionsHeight}`);
    assert(Math.abs(g.footer.actionsGap - (c.id === 'S35' ? 12 : 0)) <= 1, `${c.id}: action-row gap ${g.footer.actionsGap}`);
    assert.equal(g.footer.waitingRows, 0, `${c.id}: no separate save waiting row`);
    assert.equal(g.footer.actionsPosition, 'static', `${c.id}: footer actions do not become sticky on mobile`);
    assert(['transparent', 'rgba(0, 0, 0, 0)'].includes(g.footer.actionsBackground), `${c.id}: no obsolete footer backdrop`);
  }
  if (c.id === 'S34') {
    assert.equal(g.footer.state, 'saving'); assert.equal(g.footer.buttonBusy, 'true');
    assert.equal(g.footer.savingTextCount, 1, 'Exactly one saving label in the screen');
    assert.equal(g.footer.spinnerInButton, 1); assert.equal(g.footer.frameSpinnerCount, 1); assert.equal(g.footer.frameWaitingRows, 0);
  }
  if (c.id === 'S33') assert.equal(g.footer.state, 'unsaved');
  if (c.id === 'S35') assert.equal(g.footer.state, 'error');
  if (c.id === 'S32') {
    assert(g.loadError, 'Load failure uses the common error alert'); assert.equal(g.loadError.icons, 1);
    assert(g.loadError.borders.every(border => border.width >= 1 && border.style !== 'none'), 'Framed load alert');
    assert(!['transparent', 'rgba(0, 0, 0, 0)'].includes(g.loadError.background), 'Load alert has its error surface');
    assert.equal(g.loadError.display, 'grid'); assert(Math.abs(g.loadError.retryGap - 14) <= 1, `Retry gap ${g.loadError.retryGap}`);
  }
  if (g.feature) { assert.equal(g.feature.display, 'grid'); assert.equal(g.feature.gap, 12); }
  assert(g.tableHeaders.every(align => align === 'right'), `${c.id}: switch headers align right`);
  assert(g.tableCells.every(cell => cell.align === 'right' && (cell.inset === null || Math.abs(cell.inset - 12) <= 1)), `${c.id}: switch cells/inset`);
  assert(g.links.every(size => size === 12.5), `${c.id}: action-link text follows the common rule`);
  assert(g.reviewFieldGaps.every(gap => gap >= 15.5), `${c.id}: review warning does not touch fields`);
  assert(g.policyGaps.every(gap => gap >= 15.5), `${c.id}: policy scope does not touch following content`);
}

export async function checkActionLinkQuality(page, capture) {
  const header = page.locator('[data-data-policy] .ui-switch-column').first();
  await header.scrollIntoViewIfNeeded(); if (capture) await capture('data-table');
  const link = page.locator('[data-open-message="greeting"]'); await link.hover();
  const style = await link.evaluate(element => { const s = getComputedStyle(element); return { size: parseFloat(s.fontSize), line: s.textDecorationLine, decoration: s.textDecorationStyle }; });
  assert.equal(style.size, 12.5); assert(style.line.includes('underline')); assert.equal(style.decoration, 'dotted');
  if (capture) await capture('link-hover'); return style;
}

function copyAppearance(element) {
  const style = getComputedStyle(element), icon = element.querySelector('svg'), accent = style.getPropertyValue('--accent').trim();
  const hex = accent.match(/^#([\da-f]{6})$/i), normalized = value => value.replaceAll(/\s/g, '').toLowerCase();
  const expected = hex ? `rgb(${[0, 2, 4].map(index => parseInt(hex[1].slice(index, index + 2), 16)).join(',')})` : accent;
  return { state: element.dataset.copyState, color: style.color, accent, accentMatches: normalized(style.color) === normalized(expected),
    background: style.backgroundColor, borders: ['Top', 'Right', 'Bottom', 'Left'].map(side => parseFloat(style[`border${side}Width`])),
    outline: parseFloat(style.outlineWidth), outlineStyle: style.outlineStyle, shadow: style.boxShadow,
    iconWidth: icon?.getBoundingClientRect().width, iconHeight: icon?.getBoundingClientRect().height };
}
function validateCopyAppearance(style, accent = false) {
  assert(['transparent', 'rgba(0, 0, 0, 0)'].includes(style.background), 'Copy has no button surface');
  assert(style.borders.every(width => width === 0)); assert.equal(style.outline, 0); assert.equal(style.shadow, 'none');
  assert.equal(style.iconWidth, 18); assert.equal(style.iconHeight, 18);
  if (accent) assert(style.accentMatches, `Copy color ${style.color} differs from accent ${style.accent}`);
}
export async function checkNativeCopy(page, capture) {
  const button = page.locator('[data-new-key-once] .ea-key-copy');
  assert.equal(await button.count(), 1); assert.equal((await button.innerText()).trim(), '', 'Icon-only copy');
  await button.scrollIntoViewIfNeeded(); await page.mouse.move(0, 0);
  const idle = await button.evaluate(copyAppearance); assert.equal(idle.state, 'idle'); validateCopyAppearance(idle);
  await button.hover(); const hover = await button.evaluate(copyAppearance); validateCopyAppearance(hover, true);
  // Observe genuine rendered transitions. Clipboard and browser methods remain untouched.
  const timing = button.evaluate(element => new Promise(resolve => {
    let copiedAt = null, finished = false; const states = [];
    const finish = result => { if (finished) return; finished = true; observer.disconnect(); clearTimeout(timeout); resolve({ ...result, states }); };
    const read = () => { const state = element.dataset.copyState; states.push(state);
      if (state === 'copied' && copiedAt === null) copiedAt = performance.now();
      if (state === 'idle' && copiedAt !== null) finish({ copiedDuration: performance.now() - copiedAt });
      if (state === 'error') finish({ error: 'Native clipboard write failed' });
    };
    const observer = new MutationObserver(read);
    const timeout = setTimeout(() => finish({ error: 'Native copy feedback did not reset' }), 7000);
    observer.observe(element, { attributes: true, attributeFilter: ['data-copy-state'] });
    read();
  }));
  await page.bringToFront(); await button.click();
  await page.waitForFunction(() => ['copied', 'error'].includes(document.querySelector('[data-new-key-once] .ea-key-copy')?.dataset.copyState), null, { timeout: 5000 });
  const copied = await button.evaluate(copyAppearance); assert.equal(copied.state, 'copied', 'The native write must succeed'); validateCopyAppearance(copied, true);
  if (capture) await capture('native-key-copied');
  const feedback = await timing; assert(!feedback.error, feedback.error);
  assert(feedback.copiedDuration >= 2000, `Copied feedback too brief: ${feedback.copiedDuration}ms`);
  assert(Math.abs(feedback.copiedDuration - 3000) <= 750, `Expected a 3-second reset, observed ${feedback.copiedDuration}ms`);
  await page.waitForFunction(() => document.querySelector('[data-new-key-once] .ea-key-copy')?.dataset.copyState === 'idle', null, { timeout: 4000 });
  const reset = await button.evaluate(copyAppearance); validateCopyAppearance(reset, true);
  return { nativeClipboardWrite: true, idle, hover, copied, reset, feedback, clipboardReadOrStub: false };
}
