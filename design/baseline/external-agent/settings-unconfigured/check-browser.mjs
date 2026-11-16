// Inspect only the static S02 via native file URLs. No servers, routes or API fixtures.
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
const baselinePath = resolve(root, '../settings-off/generated/sources.json');
const verifyAccepted = () => {
  const bytes = readFileSync(baselinePath), baseline = JSON.parse(bytes);
  assert.equal(baseline.designVersion, 'S01-5037b71a01f54b2b');
  assert.equal(sha256(bytes), manifest.acceptedS01.manifestSha256, 'Accepted S01 manifest changed');
  for (const source of baseline.sources) assert.equal(sha256(readFileSync(resolve(workspace, source.path))), source.sha256, source.path);
  return baseline.sources.length;
};
verifyAccepted();
const verification = join(root, 'verification');
mkdirSync(verification, { recursive: true });
const results = [], errors = [], network = [], screenshots = [];
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const measure = () => {
  const screen = document.querySelector('.ea-screen[data-screen="S02"]');
  const bounds = screen.getBoundingClientRect();
  const form = screen.querySelector('[data-connection-form]');
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
  return {
    width: Math.round(bounds.width), height: Math.round(bounds.height), overflow,
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    lang: document.documentElement.lang, theme: document.documentElement.dataset.theme,
    fields: form ? [...form.querySelectorAll('input')].map(input => ({ type: input.type, value: input.value })) : [],
    passwordCount: screen.querySelectorAll('input[type="password"]').length,
    outgoing: form?.querySelectorAll('[data-access-direction="outgoing"]').length ?? 0,
    incoming: form?.querySelectorAll('[data-access-direction="incoming"]').length ?? 0,
    incomingState: screen.querySelector('[data-incoming-key-state]')?.getAttribute('data-incoming-key-state'),
    readyStatuses: screen.querySelectorAll('.status-pill.healthy, .status-pill.normal, .service-alert.is-success').length,
    groups: [...screen.querySelectorAll('.settings-subnav-group')].map(group => ({
      key: group.getAttribute('aria-labelledby')?.replace('settings-group-', ''),
      items: [...group.querySelectorAll(':scope > button.settings-subnav-item')].map(button => ({
        key: button.getAttribute('data-settings-item'), active: button.getAttribute('aria-current') === 'page',
      })),
    })),
  };
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
    await page.locator('.ea-screen[data-screen="S02"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('[data-screen]').count(), 1, 'Only S02 may be displayed');
  };
  const toggle = page.locator('[data-external-toggle][role="switch"], [data-external-toggle] [role="switch"]');
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 390, 320]) {
    const test = { lang, theme, width };
    await open(test);
    const geometry = await page.evaluate(measure);
    results.push({ ...test, geometry });
    assert.equal(geometry.width, width); assert.equal(geometry.height, 980);
    assert.equal(geometry.lang, lang); assert.equal(geometry.theme, theme);
    assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
    assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
    assert(geometry.fields.length >= 3, 'Show an initially empty setup form');
    assert(geometry.fields.every(field => field.value === ''), 'No invented or saved credential value');
    assert.equal(geometry.passwordCount, 1, 'Only the empty outgoing service credential is an input');
    assert.equal(geometry.outgoing, 1); assert.equal(geometry.incoming, 1);
    assert.equal(geometry.incomingState, 'absent', 'Incoming key must not be generated by viewing the design');
    assert.equal(geometry.readyStatuses, 0, 'Enabled feature does not mean connected service');
    assert.equal(await toggle.count(), 1); assert.equal(await toggle.getAttribute('aria-checked'), 'true');
    const service = geometry.groups.find(group => group.key === 'service');
    assert.equal(service?.items.at(-1).key, 'externalExecution');
    assert.equal(service.items.at(-1).active, true);
    if ((lang === 'ru' && theme === 'light' && [1440, 390].includes(width)) || (lang === 'en' && theme === 'dark' && width === 1440)) {
      const name = `S02-${lang}-${theme}-${width}.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, name) }); screenshots.push(name);
      await page.locator('[data-incoming-key-state]').scrollIntoViewIfNeeded();
      const bottom = `S02-${lang}-${theme}-${width}-bottom.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, bottom) }); screenshots.push(bottom);
    }
  }
  for (const accent of ['#1677ff', '#e8590c']) {
    const test = { lang: 'ru', theme: 'light', width: 1440, accent };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry });
    assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
  }
  await open({ lang: 'ru', theme: 'light', width: 1440 });
  const before = await page.locator('[data-connection-form]').innerText();
  await toggle.click(); assert.equal(await toggle.getAttribute('aria-checked'), 'true');
  await toggle.focus(); await page.keyboard.press('Space');
  assert.equal(await toggle.getAttribute('aria-checked'), 'true');
  const actions = page.locator('[data-connection-form] button');
  let requiredSetupActions = 0;
  for (const action of await actions.all()) {
    if (/сохран|save|провер|check/i.test(await action.innerText())) {
      requiredSetupActions += 1;
      assert(await action.isDisabled(), 'Save and capability check stay unavailable for an empty connection');
    }
    if (await action.isEnabled()) await action.click();
  }
  assert(requiredSetupActions >= 2, 'Show disabled save and connection-check actions');
  assert.equal(await page.locator('[data-connection-form]').innerText(), before, 'No fake saving or generated key');
  assert.equal(await page.locator('[data-incoming-key-state]').getAttribute('data-incoming-key-state'), 'absent');
  assert.equal(await page.locator('[data-connection-form] input[type="password"]').inputValue(), '');
  results.push({ check: 'Static enabled state and initial actions', outcome: 'no saved result or generated key' });
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  const zoomed = await page.evaluate(measure);
  assert.equal(zoomed.width, 2880); assert.equal(zoomed.overflow.length, 0, JSON.stringify(zoomed));
  results.push({ check: '200% CSS review scale at original viewport 1510', geometry: zoomed });
  const changedSinceBuild = manifest.sources.filter(source => sha256(readFileSync(resolve(workspace, source.path))) !== source.sha256).map(source => source.path);
  assert.deepEqual(changedSinceBuild, [], 'Repeat after any source changes');
  const acceptedSources = verifyAccepted();
  assert.equal(network.length, 0, JSON.stringify(network)); assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log(JSON.stringify({ status: 'PASS', designVersion: manifest.designVersion, matrixCases: 16, additionalAccents: 2,
    browserErrors: errors.length, networkRequests: network.length, acceptedS01SourcesUnchanged: acceptedSources, screenshots, changedSinceBuild }));
} finally {
  writeFileSync(join(verification, 'browser-results.json'), JSON.stringify({ designVersion: manifest.designVersion,
    scope: 'Static S02 only; no service, credential generation or integration verified', results, errors, network, screenshots }, null, 2) + '\n');
  await browser.close();
}
