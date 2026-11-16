// Inspect only static S06 via a native file URL. No server, routes, fixtures or API substitutes.
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
assert.deepEqual(manifest.screens, ['S06']);
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
let status = 'RUNNING';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const measure = () => {
  const screen = document.querySelector('.ea-screen[data-screen="S06"]'), bounds = screen.getBoundingClientRect();
  const shell = screen.querySelector('.hub-shell'), shellBounds = shell.getBoundingClientRect();
  const panel = screen.querySelector('.agent-test-panel'), panelBounds = panel.getBoundingClientRect();
  const scale = bounds.width / screen.clientWidth;
  const overflow = [];
  const regions = {};
  const regionsSelector = '.agent-test-head, .agent-action-test-mode, .agent-test-data, .agent-test-feed, [data-external-waiting], .agent-test-composer';
  for (const element of screen.querySelectorAll(`.agent-page, .agent-card, .agent-head, .agent-grid, .agent-column, .agent-test-panel, ${regionsSelector}, .agent-test-client > div`)) {
    const style = getComputedStyle(element), rect = element.getBoundingClientRect();
    if (style.display === 'none' || !rect.width || !rect.height) continue;
    const boundary = element.closest('.agent-test-panel') ? panelBounds : shellBounds;
    if (rect.left < boundary.left - 1 || rect.right > boundary.right + 1 || element.scrollWidth > element.clientWidth + 1) {
      overflow.push({ className: String(element.className), clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth, left: Math.round(rect.left - boundary.left), right: Math.round(rect.right - boundary.right) });
    }
    if (element.matches(regionsSelector)) regions[element.className] = {
      top: Math.round((rect.top - panelBounds.top) / scale), height: Math.round(rect.height / scale), width: Math.round(rect.width / scale),
    };
  }
  const mode = panel.querySelector('.agent-action-test-mode'), feed = panel.querySelector('.agent-test-feed');
  const waiting = panel.querySelector('[data-external-waiting]'), bubble = panel.querySelector('.agent-test-client > div');
  const composer = panel.querySelector('.agent-test-composer'), input = composer?.querySelector('input');
  const headerButtons = [...panel.querySelectorAll('.agent-test-head button')];
  const settingFields = [...screen.querySelectorAll('input, textarea, .readonly-field')].filter(field => {
    const label = field.matches('.readonly-field') ? field.querySelector(':scope > span')?.textContent : field.closest('label')?.querySelector('span')?.textContent;
    return /external\s*agent\s*id|externalAgentId|тайм.?аут|timeout|https?.?адрес|service\s*url|endpoint|исходящий.*ключ|входящий.*ключ|outgoing.*key|incoming.*key/i.test(label ?? '');
  }).map(field => field.textContent?.trim().slice(0, 120));
  return {
    width: Math.round(bounds.width), height: Math.round(bounds.height), scale, overflow, regions,
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    shellWidth: Math.round(shellBounds.width / scale), shellMinWidth: getComputedStyle(shell).minWidth,
    lang: document.documentElement.lang, theme: document.documentElement.dataset.theme,
    panelCount: screen.querySelectorAll('.agent-test-panel').length, panelRole: panel.getAttribute('role'),
    testState: panel.getAttribute('data-test-state'), panelParent: panel.parentElement.className, panelPosition: getComputedStyle(panel).position,
    panelWidth: Math.round(panelBounds.width / scale), panelHeight: Math.round(panelBounds.height / scale),
    panelRight: Math.round((panelBounds.right - shellBounds.right) / scale), panelTop: Math.round((panelBounds.top - shellBounds.top) / scale),
    panelNamed: Boolean(panel.getAttribute('aria-labelledby') && document.getElementById(panel.getAttribute('aria-labelledby'))?.textContent.trim()),
    externalMode: Boolean(mode?.hasAttribute('data-external-test')), modeWarning: Boolean(mode?.classList.contains('is-warning')),
    modeNote: mode?.textContent.trim(), modeButtons: mode?.querySelectorAll('button, [role="tab"], [role="radio"], input, select').length,
    headerStatus: screen.querySelector('.agent-head .agents-status')?.textContent.trim(),
    activeTestButton: Boolean(screen.querySelector('.agent-test-button.is-active[aria-expanded="true"]')),
    autonomousSwitch: screen.querySelector('.agent-assistance .is-comparison')?.getAttribute('aria-checked'),
    panelInputCount: panel.querySelectorAll('input, textarea, select').length,
    clientDataCount: panel.querySelectorAll('.agent-test-data').length,
    clientDataPolicy: panel.querySelector('.agent-test-data')?.getAttribute('data-external-test-data'),
    clientDataInputs: panel.querySelectorAll('.agent-test-data input, .agent-test-data textarea, .agent-test-data select').length,
    clientDataDisabled: panel.querySelector('.agent-test-data-heading')?.disabled,
    feedCount: panel.querySelectorAll('.agent-test-feed').length, feedRole: feed?.getAttribute('role'), feedLive: feed?.getAttribute('aria-live'),
    feedBusy: feed?.getAttribute('aria-busy'), feedOverflow: feed && getComputedStyle(feed).overflowY,
    feedHasWaiting: Boolean(feed?.contains(waiting)), clientCount: feed?.querySelectorAll('.agent-test-client').length,
    clientText: bubble?.textContent.trim(), bubbleWrap: bubble && getComputedStyle(bubble).overflowWrap,
    bubbleWhiteSpace: bubble && getComputedStyle(bubble).whiteSpace,
    waitingCount: panel.querySelectorAll('[data-external-waiting]').length, waitingRole: waiting?.getAttribute('role'),
    waitingName: waiting?.getAttribute('aria-label'), waitingText: waiting?.textContent.trim(),
    waitingHeight: waiting && Math.round(waiting.getBoundingClientRect().height / scale),
    waitingMinHeight: waiting && getComputedStyle(waiting).minHeight,
    commonSpinner: waiting?.querySelectorAll('.logo-spinner.cb-loader[role="status"] animate[attributeName="d"]').length,
    composerValue: input?.value, composerDisabled: input?.disabled,
    sendDisabled: composer?.querySelector('button[type="submit"]')?.disabled,
    sendBusy: composer?.querySelector('button[type="submit"]')?.getAttribute('aria-busy'),
    composerInsidePanel: Boolean(composer && composer.getBoundingClientRect().bottom <= panelBounds.bottom + 1),
    headerDisabled: headerButtons.map(button => button.disabled),
    responseNodes: panel.querySelectorAll('.agent-test-reply, .agent-test-error, .tool-call-chip, .agent-action-test-result, .agent-action-test-preview').length,
    skillsWarning: panel.querySelectorAll('.agent-tools-warning, .skills-model-warning, .skill-model-warning, .agent-model-warning').length,
    globalBlockers: screen.querySelectorAll('.agent-blocker').length,
    passwordFields: screen.querySelectorAll('input[type="password"]').length, settingFields,
    endpointValues: [...screen.querySelectorAll('input')].map(field => field.value).filter(value => /^https?:\/\//i.test(value)),
  };
};
const validate = (geometry, test) => {
  assert.equal(geometry.width, test.width); assert.equal(geometry.height, 980);
  assert.equal(geometry.lang, test.lang); assert.equal(geometry.theme, test.theme);
  assert.deepEqual(geometry.overflow, [], JSON.stringify({ test, geometry }));
  assert.equal(geometry.shellMinWidth, '1024px'); assert.equal(geometry.shellWidth, Math.max(1024, test.width));
  if (test.width < 1024) assert(geometry.scrollWidth >= 1024, 'Narrow agent preview intentionally scrolls horizontally');
  else assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
  assert.equal(geometry.panelCount, 1); assert.equal(geometry.panelRole, 'dialog'); assert(geometry.panelNamed);
  assert.equal(geometry.testState, 'waiting'); assert(/\bagent-page\b/.test(geometry.panelParent)); assert.equal(geometry.panelPosition, 'absolute');
  assert.equal(geometry.panelWidth, 420); assert.equal(geometry.panelHeight, 980);
  assert.equal(geometry.panelRight, 0); assert.equal(geometry.panelTop, 0);
  assert(geometry.externalMode); assert(geometry.modeWarning); assert(geometry.modeNote); assert.equal(geometry.modeButtons, 0);
  assert.equal(geometry.headerStatus, test.lang === 'ru' ? 'Без AI' : 'No AI');
  assert(geometry.activeTestButton); assert.equal(geometry.autonomousSwitch, 'false');
  assert.equal(geometry.panelInputCount, 1); assert.equal(geometry.clientDataCount, 1); assert.equal(geometry.clientDataInputs, 0);
  assert.equal(geometry.clientDataPolicy, 'empty'); assert.equal(geometry.clientDataDisabled, true);
  assert.equal(geometry.feedCount, 1); assert.equal(geometry.feedRole, 'log'); assert.equal(geometry.feedLive, 'polite');
  assert.notEqual(geometry.feedBusy, 'true', 'The waiting announcement must remain available in the log');
  assert(['auto', 'scroll'].includes(geometry.feedOverflow)); assert(geometry.feedHasWaiting);
  assert.equal(geometry.clientCount, 1); assert(geometry.clientText);
  assert.equal(geometry.bubbleWrap, 'anywhere'); assert.equal(geometry.bubbleWhiteSpace, 'pre-wrap');
  assert.equal(geometry.waitingCount, 1); assert.equal(geometry.waitingRole, 'status');
  assert(geometry.waitingName); assert(geometry.waitingText.includes(geometry.waitingName));
  assert.equal(geometry.commonSpinner, 1); assert(geometry.waitingHeight >= 88); assert.equal(geometry.waitingMinHeight, '88px');
  assert.equal(geometry.composerValue, ''); assert.equal(geometry.composerDisabled, true);
  assert.equal(geometry.sendDisabled, true); assert.equal(geometry.sendBusy, 'true'); assert(geometry.composerInsidePanel);
  assert.deepEqual(geometry.headerDisabled, [true, false]); assert.equal(geometry.responseNodes, 0); assert.equal(geometry.skillsWarning, 0);
  assert.equal(geometry.globalBlockers, 0); assert.equal(geometry.passwordFields, 0);
  assert.deepEqual(geometry.settingFields, []); assert.deepEqual(geometry.endpointValues, []);
};
try {
  const page = await browser.newPage({ viewport: { width: 1510, height: 1120 } });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  const open = async ({ lang, theme, width, accent = '#0f9b8e' }) => {
    const url = new URL('waiting.dc.html', import.meta.url);
    url.search = new URLSearchParams({ lang, theme, width: String(width), height: '980', accent });
    await page.goto(url.href, { waitUntil: 'load' });
    await page.locator('.ea-screen[data-screen="S06"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('[data-screen]').count(), 1, 'Only S06 may be displayed');
  };
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 390, 320]) {
    const test = { lang, theme, width };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry }); validate(geometry, test);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.deepEqual((await page.evaluate(measure)).regions, geometry.regions, 'Waiting animation cannot move panel regions');
    if ((lang === 'ru' && theme === 'light' && [1440, 390].includes(width)) || (lang === 'en' && theme === 'dark' && width === 1440)) {
      const name = `S06-${lang}-${theme}-${width}.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, name) }); screenshots.push(name);
      await page.locator('.hub-scroll').evaluate(element => { element.scrollTop = element.scrollHeight; });
      await page.locator('.agent-test-feed').evaluate(element => { element.scrollTop = element.scrollHeight; });
      const bottom = `S06-${lang}-${theme}-${width}-bottom.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, bottom) }); screenshots.push(bottom);
      if (width < 1024) {
        await page.locator('.ea-screen').evaluate(element => { element.scrollLeft = element.scrollWidth; });
        const right = `S06-${lang}-${theme}-${width}-scrolled-right.png`;
        await page.locator('.ea-screen').screenshot({ path: join(verification, right) }); screenshots.push(right);
      }
    }
  }
  for (const accent of ['#1677ff', '#e8590c']) {
    const test = { lang: 'ru', theme: 'light', width: 1440, accent };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry }); validate(geometry, test);
  }
  await open({ lang: 'ru', theme: 'light', width: 1440 });
  const before = await page.locator('.ea-screen').innerText(), beforeGeometry = await page.evaluate(measure);
  assert(await page.locator('.agent-test-head button').first().isDisabled());
  await page.locator('.agent-test-head button').last().click();
  await page.locator('.agent-test-panel').focus(); await page.keyboard.press('Escape');
  assert.equal(await page.locator('.ea-screen').innerText(), before, 'Closing cannot simulate cancellation or change this static waiting frame');
  const afterGeometry = await page.evaluate(measure);
  validate(afterGeometry, { lang: 'ru', theme: 'light', width: 1440 });
  assert.deepEqual(afterGeometry.regions, beforeGeometry.regions);
  results.push({ check: 'Static waiting actions and geometry', outcome: 'close/Escape inert; no cancellation, restart, send, response or layout movement' });
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  const zoomed = await page.evaluate(measure);
  assert.equal(zoomed.width, 2880); assert.deepEqual(zoomed.overflow, [], JSON.stringify(zoomed));
  assert.equal(zoomed.panelWidth, 420); assert(zoomed.composerInsidePanel);
  results.push({ check: '200% CSS review scale at original viewport 1510', geometry: zoomed });
  const changedSinceBuild = manifest.sources.filter(source => sha256(readFileSync(resolve(workspace, source.path))) !== source.sha256).map(source => source.path);
  assert.deepEqual(changedSinceBuild, [], 'Repeat checks after any source edit');
  const accepted = verifyAccepted(); assert.deepEqual(network, []); assert.deepEqual(errors, []);
  status = 'PASS';
  console.log(JSON.stringify({ status, designVersion: manifest.designVersion, matrixCases: 16, additionalAccents: 2,
    browserErrors: errors.length, networkRequests: network.length, acceptedScreens: accepted, screenshots, changedSinceBuild,
    limitations: manifest.limitations }));
} catch (error) {
  status = 'FAIL';
  throw error;
} finally {
  writeFileSync(join(verification, 'browser-results.json'), JSON.stringify({ status, designVersion: manifest.designVersion,
    scope: manifest.scope, limitations: manifest.limitations, results, errors, network, screenshots }, null, 2) + '\n');
  await browser.close();
}
