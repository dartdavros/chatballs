// Inspect only the static S03 using native file URLs. No server, routes or API fixtures.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url)), workspace = resolve(root, '../../../..');
const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencies = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, common)), 'node_modules');
const require = createRequire(import.meta.url);
const { chromium } = require(require.resolve('@playwright/test', { paths: [workspace, dirname(dependencies)] }));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const manifest = JSON.parse(readFileSync(join(root, 'generated/sources.json'), 'utf8'));
const verifyAccepted = () => manifest.acceptedScreens.map(accepted => {
  const bytes = readFileSync(resolve(root, `../${accepted.folder}/generated/sources.json`)), baseline = JSON.parse(bytes);
  assert.equal(baseline.designVersion, accepted.designVersion);
  assert.equal(sha256(bytes), accepted.manifestSha256, `Accepted manifest changed: ${accepted.folder}`);
  for (const source of baseline.sources) assert.equal(sha256(readFileSync(resolve(workspace, source.path))), source.sha256, source.path);
  return { version: baseline.designVersion, sourceHashesUnchanged: baseline.sources.length };
});
verifyAccepted();
const verification = join(root, 'verification');
mkdirSync(verification, { recursive: true });
const results = [], errors = [], network = [], screenshots = [];
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const measure = () => {
  const screen = document.querySelector('.ea-screen[data-screen="S03"]'), bounds = screen.getBoundingClientRect();
  const ready = screen.querySelector('[data-connection-state="ready"]');
  const overflow = [];
  for (const element of screen.querySelectorAll('*')) {
    const style = getComputedStyle(element), rect = element.getBoundingClientRect();
    if (style.display === 'none' || style.visibility === 'hidden' || !rect.width || !rect.height) continue;
    if (rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1) continue;
    let clipped = false;
    for (let parent = element.parentElement; parent && parent !== screen; parent = parent.parentElement) {
      if (/auto|scroll|hidden|clip/.test(getComputedStyle(parent).overflowX)) { clipped = true; break; }
    }
    if (!clipped) overflow.push({ tag: element.tagName, className: String(element.className).slice(0, 90) });
  }
  const secretFields = [...screen.querySelectorAll('[data-saved-secret]')].map(wrapper => {
    const input = wrapper.querySelector('input');
    return { direction: wrapper.getAttribute('data-saved-secret'), count: wrapper.querySelectorAll('input').length,
      type: input?.type, value: input?.value, attributeValue: input?.getAttribute('value'), placeholder: input?.placeholder,
      readOnly: input?.readOnly, disabled: input?.disabled };
  });
  return { width: Math.round(bounds.width), height: Math.round(bounds.height), overflow,
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    lang: document.documentElement.lang, theme: document.documentElement.dataset.theme,
    ready: Boolean(ready), secretFields,
    ordinaryFields: [...screen.querySelectorAll('input:not([type="password"])')].map(input => input.value),
    passwordCount: screen.querySelectorAll('input[type="password"]').length,
    incomingState: screen.querySelector('[data-incoming-key-state]')?.getAttribute('data-incoming-key-state'),
    capabilitiesHealthy: screen.querySelectorAll('[data-capabilities-result] .status-pill.healthy').length,
    forbiddenSecretActions: [...screen.querySelectorAll('button')].map(button => button.textContent.trim())
      .filter(text => /раскрыть|показать.*ключ|копир|создать.*ключ|reveal|show.*key|copy|create.*key/i.test(text)),
    groups: [...screen.querySelectorAll('.settings-subnav-group')].map(group => ({
      key: group.getAttribute('aria-labelledby')?.replace('settings-group-', ''),
      items: [...group.querySelectorAll(':scope > button.settings-subnav-item')].map(button => ({
        key: button.getAttribute('data-settings-item'), active: button.getAttribute('aria-current') === 'page',
      })),
    })),
  };
};
const validate = (geometry, test) => {
  assert.equal(geometry.width, test.width); assert.equal(geometry.height, 980);
  assert.equal(geometry.lang, test.lang); assert.equal(geometry.theme, test.theme);
  assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
  assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
  assert(geometry.ready, 'This frame depicts configured connection readiness');
  assert.equal(geometry.passwordCount, 2); assert.equal(geometry.secretFields.length, 2);
  assert.deepEqual(geometry.secretFields.map(field => field.direction).sort(), ['incoming', 'outgoing']);
  for (const field of geometry.secretFields) {
    assert.equal(field.count, 1); assert.equal(field.type, 'password'); assert.equal(field.value, '');
    assert(!field.attributeValue, 'No underlying secret value, including an illustrative token');
    assert(/^[•●·]+$/.test(field.placeholder), 'Only a static mask placeholder is allowed');
    assert(field.readOnly || field.disabled, 'Saved keys cannot expose editable or recoverable values');
  }
  assert(geometry.ordinaryFields.includes('https://agent.example'), 'Use the reserved illustrative service endpoint');
  assert(geometry.ordinaryFields.filter(Boolean).length >= 2, 'Show the saved name and HTTPS address');
  assert.equal(geometry.incomingState, 'created'); assert(geometry.capabilitiesHealthy >= 1);
  assert.equal(geometry.forbiddenSecretActions.length, 0, 'Reading the card cannot reveal/copy/recreate a saved key');
  const service = geometry.groups.find(group => group.key === 'service');
  assert.equal(service?.items.at(-1).key, 'externalExecution'); assert.equal(service.items.at(-1).active, true);
};
try {
  const page = await browser.newPage({ viewport: { width: 1510, height: 1120 } });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  const open = async ({ lang, theme, width, accent = '#0f9b8e' }) => {
    const url = new URL('settings.dc.html', import.meta.url);
    url.search = new URLSearchParams({ lang, theme, width: String(width), height: '980', accent });
    await page.goto(url.href, { waitUntil: 'load' });
    await page.locator('.ea-screen[data-screen="S03"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('[data-screen]').count(), 1, 'Only S03 may be displayed');
  };
  const toggle = page.locator('[data-external-toggle][role="switch"], [data-external-toggle] [role="switch"]');
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 390, 320]) {
    const test = { lang, theme, width };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry });
    validate(geometry, test); assert.equal(await toggle.count(), 1); assert.equal(await toggle.getAttribute('aria-checked'), 'true');
    if ((lang === 'ru' && theme === 'light' && [1440, 390].includes(width)) || (lang === 'en' && theme === 'dark' && width === 1440)) {
      const name = `S03-${lang}-${theme}-${width}.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, name) }); screenshots.push(name);
      await page.locator('.settings-content').evaluate(element => { element.scrollTop = element.scrollHeight; });
      const bottom = `S03-${lang}-${theme}-${width}-bottom.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, bottom) }); screenshots.push(bottom);
    }
  }
  for (const accent of ['#1677ff', '#e8590c']) {
    const test = { lang: 'ru', theme: 'light', width: 1440, accent };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry }); validate(geometry, test);
  }
  await open({ lang: 'ru', theme: 'light', width: 1440 });
  const before = await page.locator('.ea-screen').innerText();
  await toggle.click(); await toggle.focus(); await page.keyboard.press('Space');
  assert.equal(await toggle.getAttribute('aria-checked'), 'true');
  let inactiveSave = 0, inertActions = 0;
  for (const action of await page.locator('[data-connection-state="ready"] button').all()) {
    const label = await action.innerText();
    if (/сохран|save/i.test(label)) { inactiveSave += 1; assert(await action.isDisabled(), 'A clean saved form has no pending save'); }
    else if (await action.isEnabled()) { await action.click(); inertActions += 1; }
  }
  assert(inactiveSave >= 1); assert(inertActions >= 1, 'Show existing check/replace/revoke action controls');
  assert.equal(await page.locator('.ea-screen').innerText(), before, 'Static actions cannot rotate/revoke/reveal or simulate a new check');
  validate(await page.evaluate(measure), { lang: 'ru', theme: 'light', width: 1440 });
  results.push({ check: 'Static ready actions', outcome: 'no key, status or content changed' });
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  const zoomed = await page.evaluate(measure);
  assert.equal(zoomed.width, 2880); assert.equal(zoomed.overflow.length, 0, JSON.stringify(zoomed));
  results.push({ check: '200% CSS review scale at original viewport 1510', geometry: zoomed });
  const changedSinceBuild = manifest.sources.filter(source => sha256(readFileSync(resolve(workspace, source.path))) !== source.sha256).map(source => source.path);
  assert.deepEqual(changedSinceBuild, [], 'Repeat checks after any source edit');
  const accepted = verifyAccepted(); assert.equal(network.length, 0, JSON.stringify(network)); assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log(JSON.stringify({ status: 'PASS', designVersion: manifest.designVersion, matrixCases: 16, additionalAccents: 2,
    browserErrors: errors.length, networkRequests: network.length, acceptedScreens: accepted, screenshots, changedSinceBuild }));
} finally {
  writeFileSync(join(verification, 'browser-results.json'), JSON.stringify({ designVersion: manifest.designVersion,
    scope: 'Static S03 connection readiness only; no real check, key, agent execution or delivery verified', results, errors, network, screenshots }, null, 2) + '\n');
  await browser.close();
}
