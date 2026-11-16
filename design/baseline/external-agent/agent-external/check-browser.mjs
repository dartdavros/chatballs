// Inspect only static S04 via a native file URL. No server, routes, fixtures or API substitutes.
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
assert.deepEqual(manifest.screens, ['S04']);
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
  const screen = document.querySelector('.ea-screen[data-screen="S04"]'), bounds = screen.getBoundingClientRect();
  const shell = screen.querySelector('.hub-shell'), shellBounds = shell.getBoundingClientRect();
  const scale = bounds.width / screen.clientWidth;
  const overflow = [];
  for (const element of screen.querySelectorAll('.agent-page, .agent-card, .agent-head, .agent-grid, .agent-column')) {
    const style = getComputedStyle(element), rect = element.getBoundingClientRect();
    if (style.display === 'none' || !rect.width || !rect.height) continue;
    if (rect.left < shellBounds.left - 1 || rect.right > shellBounds.right + 1 || element.scrollWidth > element.clientWidth + 1) {
      overflow.push({ className: String(element.className), clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth, left: Math.round(rect.left - shellBounds.left), right: Math.round(rect.right - shellBounds.right) });
    }
  }
  const speech = screen.querySelector('.agent-speech-settings');
  const language = screen.querySelector('.agent-answer-language');
  const execution = screen.querySelector('[data-execution-mode="external"]');
  const settingFields = [...screen.querySelectorAll('input, textarea, .readonly-field')].filter(field => {
    const label = field.matches('.readonly-field') ? field.querySelector(':scope > span')?.textContent : field.closest('label')?.querySelector('span')?.textContent;
    return /external\s*agent\s*id|externalAgentId|тайм.?аут|timeout|https?.?адрес|service\s*url|endpoint|исходящий.*ключ|входящий.*ключ|outgoing.*key|incoming.*key/i.test(label ?? '');
  }).map(field => field.textContent?.trim().slice(0, 120));
  return {
    width: Math.round(bounds.width), height: Math.round(bounds.height), scale, overflow,
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    shellWidth: Math.round(shellBounds.width / scale), shellMinWidth: getComputedStyle(shell).minWidth,
    lang: document.documentElement.lang, theme: document.documentElement.dataset.theme,
    executionSelected: Boolean(execution), executorName: execution?.querySelector('[data-executor-name]')?.textContent.trim(),
    headerStatus: screen.querySelector('.agent-head .agents-status')?.textContent.trim(),
    headerCount: screen.querySelectorAll('.agent-head').length,
    draftSwitch: screen.querySelector('.agent-assistance .ui-switch:not(.is-comparison)')?.getAttribute('aria-checked'),
    autonomousSwitch: screen.querySelector('.agent-assistance .is-comparison')?.getAttribute('aria-checked'),
    independentStt: Boolean(speech?.hasAttribute('data-independent-stt')),
    sttProvider: speech?.querySelector('.readonly-field .select-value')?.textContent.trim(),
    speechText: speech?.textContent.trim(), languageIndependent: Boolean(language && !language.closest('[data-builtin-settings]')),
    builtinPreserved: Boolean(screen.querySelector('[data-builtin-preserved]')),
    mountedBuiltin: screen.querySelectorAll('[data-builtin-settings]').length,
    globalBlockers: screen.querySelectorAll('.agent-blocker').length,
    passwordFields: screen.querySelectorAll('input[type="password"]').length, settingFields,
    endpointValues: [...screen.querySelectorAll('input')].map(input => input.value).filter(value => /^https?:\/\//i.test(value)),
  };
};
const validate = (geometry, test) => {
  assert.equal(geometry.width, test.width); assert.equal(geometry.height, 980);
  assert.equal(geometry.lang, test.lang); assert.equal(geometry.theme, test.theme);
  assert.deepEqual(geometry.overflow, [], JSON.stringify({ test, geometry }));
  assert.equal(geometry.shellMinWidth, '1024px', 'Keep the current non-chat shell limitation');
  assert.equal(geometry.shellWidth, Math.max(1024, test.width));
  if (test.width < 1024) assert(geometry.scrollWidth >= 1024, 'Narrow agent preview intentionally scrolls horizontally');
  else assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
  assert(geometry.executionSelected); assert(geometry.executorName, 'Show the configured executor name');
  assert.equal(geometry.headerCount, 1); assert.equal(geometry.headerStatus, test.lang === 'ru' ? 'Без AI' : 'No AI');
  assert.equal(geometry.draftSwitch, 'true'); assert.equal(geometry.autonomousSwitch, 'false');
  assert(geometry.independentStt); assert(geometry.sttProvider, 'STT provider must be chosen explicitly');
  assert(!/как у ответов|same as answers/i.test(geometry.speechText));
  assert(geometry.languageIndependent); assert(geometry.builtinPreserved); assert.equal(geometry.mountedBuiltin, 0);
  assert.equal(geometry.globalBlockers, 0, 'A missing built-in LLM cannot block external responses');
  assert.equal(geometry.passwordFields, 0); assert.deepEqual(geometry.settingFields, []); assert.deepEqual(geometry.endpointValues, []);
};
try {
  const page = await browser.newPage({ viewport: { width: 1510, height: 1120 } });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  const open = async ({ lang, theme, width, accent = '#0f9b8e' }) => {
    const url = new URL('agent.dc.html', import.meta.url);
    url.search = new URLSearchParams({ lang, theme, width: String(width), height: '980', accent });
    await page.goto(url.href, { waitUntil: 'load' });
    await page.locator('.ea-screen[data-screen="S04"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('[data-screen]').count(), 1, 'Only S04 may be displayed');
  };
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 390, 320]) {
    const test = { lang, theme, width };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry }); validate(geometry, test);
    if ((lang === 'ru' && theme === 'light' && [1440, 390].includes(width)) || (lang === 'en' && theme === 'dark' && width === 1440)) {
      const name = `S04-${lang}-${theme}-${width}.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, name) }); screenshots.push(name);
      await page.locator('.hub-scroll').evaluate(element => { element.scrollTop = element.scrollHeight; });
      const bottom = `S04-${lang}-${theme}-${width}-bottom.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, bottom) }); screenshots.push(bottom);
      if (width < 1024) {
        await page.locator('.ea-screen').evaluate(element => { element.scrollLeft = element.scrollWidth; });
        const right = `S04-${lang}-${theme}-${width}-scrolled-right.png`;
        await page.locator('.ea-screen').screenshot({ path: join(verification, right) }); screenshots.push(right);
      }
    }
  }
  for (const accent of ['#1677ff', '#e8590c']) {
    const test = { lang: 'ru', theme: 'light', width: 1440, accent };
    await open(test); const geometry = await page.evaluate(measure); results.push({ ...test, geometry }); validate(geometry, test);
  }
  await open({ lang: 'ru', theme: 'light', width: 1440 });
  const before = await page.locator('.ea-screen').innerText();
  for (const selector of ['.agent-toggle', '.agent-test-button', '.agent-assistance .ui-switch:not(.is-comparison)']) {
    const action = page.locator(selector); assert.equal(await action.count(), 1); await action.click();
  }
  assert.equal(await page.locator('.ea-screen').innerText(), before, 'Preview actions must not activate, test or change assistance');
  assert.equal(await page.locator('.agent-test-panel').count(), 0, 'No execution test may be mounted');
  await page.locator('.agent-head-menu').click();
  const contextMenu = page.locator('.ant-dropdown.app-dropdown:not(.is-field):visible'); await contextMenu.waitFor();
  assert((await contextMenu.innerText()).trim(), 'The actual agent context menu can be inspected');
  await page.locator('.agent-head-menu').click();
  await contextMenu.waitFor({ state: 'hidden' });
  await page.locator('.agent-speech-settings .readonly-field .select-box').first().click();
  const speechMenu = page.locator('.ant-dropdown.app-dropdown.is-field:visible'); await speechMenu.waitFor();
  const speechOptions = await speechMenu.innerText();
  assert(speechOptions.trim()); assert(!/как у ответов|same as answers/i.test(speechOptions), speechOptions);
  await page.locator('.agent-speech-settings .readonly-field .select-box').first().click();
  await speechMenu.waitFor({ state: 'hidden' });
  assert.equal(await page.locator('.ea-screen').innerText(), before, 'Inspecting selections cannot change this frame');
  validate(await page.evaluate(measure), { lang: 'ru', theme: 'light', width: 1440 });
  results.push({ check: 'Static actions and independent STT menu', outcome: 'no execution, state mutation or inherited STT option' });
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  const zoomed = await page.evaluate(measure);
  assert.equal(zoomed.width, 2880); assert.equal(zoomed.overflow.length, 0, JSON.stringify(zoomed));
  results.push({ check: '200% CSS review scale at original viewport 1510', geometry: zoomed });
  const changedSinceBuild = manifest.sources.filter(source => sha256(readFileSync(resolve(workspace, source.path))) !== source.sha256).map(source => source.path);
  assert.deepEqual(changedSinceBuild, [], 'Repeat checks after any source edit');
  const accepted = verifyAccepted(); assert.deepEqual(network, []); assert.deepEqual(errors, []);
  status = 'PASS';
  console.log(JSON.stringify({ status: 'PASS', designVersion: manifest.designVersion, matrixCases: 16, additionalAccents: 2,
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
