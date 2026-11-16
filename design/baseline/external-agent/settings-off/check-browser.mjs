// Check the one static S01 in installed Chrome via file URLs. No server or API mocks.
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
const manifest = JSON.parse(readFileSync(join(root, 'generated/sources.json'), 'utf8'));
const serverIconPath = readFileSync(join(workspace, 'apps/internal-ui/src/shared/icons.tsx'), 'utf8')
  .match(/^\s*server:\s*<path d="([^"]+)"/m)?.[1];
assert(serverIconPath, 'Expected the existing shared server icon');
const verification = join(root, 'verification');
mkdirSync(verification, { recursive: true });
const results = [], errors = [], network = [], screenshots = [];
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const measure = () => {
  const screen = document.querySelector('.ea-screen[data-screen="S01"]');
  const shell = screen.querySelector('.hub-shell');
  const bounds = screen.getBoundingClientRect();
  const externalCard = screen.querySelector('[data-external-card]');
  const externalBounds = externalCard?.getBoundingClientRect();
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
    width: Math.round(bounds.width), height: Math.round(bounds.height),
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    shellWidth: Math.round(shell.getBoundingClientRect().width), shellMinWidth: getComputedStyle(shell).minWidth,
    overflow, language: document.documentElement.lang, theme: document.documentElement.dataset.theme,
    passwordFields: screen.querySelectorAll('input[type="password"]').length,
    configurationFields: screen.querySelectorAll('[data-external-config], [data-external-endpoint], [data-external-agent-id]').length,
    organizationForms: screen.querySelectorAll('.settings-content .administration-organization').length,
    retentionSections: screen.querySelectorAll('.settings-content .run-retention').length,
    heading: screen.querySelector('.settings-head h2')?.textContent.trim(),
    settingsGroups: [...screen.querySelectorAll('.settings-subnav-group')].map(group => ({
      key: group.getAttribute('aria-labelledby')?.replace('settings-group-', ''),
      items: [...group.querySelectorAll(':scope > button.settings-subnav-item')].map(button => ({
        key: button.getAttribute('data-settings-item'), label: button.textContent.trim(),
        active: button.getAttribute('aria-current') === 'page', iconPath: button.querySelector('svg path')?.getAttribute('d'),
      })),
    })),
    badLinks: [...screen.querySelectorAll('a')].filter(a => a.getAttribute('href') === '#').length,
    externalCard: externalBounds ? {
      left: externalBounds.left - bounds.left, right: externalBounds.right - bounds.right,
      top: externalBounds.top - bounds.top, bottom: externalBounds.bottom - bounds.top,
      fields: externalCard.querySelectorAll('input, textarea, select, button.select-box').length,
      clientWidth: externalCard.clientWidth, scrollWidth: externalCard.scrollWidth,
    } : null,
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
    await page.locator('.ea-screen[data-screen="S01"]').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert.equal(await page.locator('[data-screen]').count(), 1, 'Only S01 may be displayed');
  };
  const offToggle = page.locator('[data-external-toggle][role="switch"], [data-external-toggle] [role="switch"]');
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 1024, 390, 320]) {
    const test = { lang, theme, width };
    await open(test);
    const geometry = await page.evaluate(measure);
    results.push({ ...test, geometry });
    assert.equal(geometry.width, width, JSON.stringify({ test, geometry }));
    assert.equal(geometry.height, 980);
    assert.equal(geometry.language, lang);
    assert.equal(geometry.theme, theme);
    assert.equal(geometry.passwordFields, 0, 'OFF state must not show credentials');
    assert.equal(geometry.configurationFields, 0, 'OFF state must not show executor setup');
    assert.equal(geometry.organizationForms, 0, 'External execution has its own section, not the organization form');
    assert.equal(geometry.retentionSections, 0, 'The external execution section must not include unrelated retention settings');
    const externalLabel = lang === 'ru' ? 'Внешнее исполнение' : 'External execution';
    assert.equal(geometry.heading, externalLabel);
    assert.deepEqual(geometry.settingsGroups.map(group => [group.key, group.items.map(item => item.key)]), [
      ['organization', ['organization', 'groups']],
      ['service', ['queue', 'rules', 'transfer', 'templates', 'communication', 'externalExecution']],
      ['quality', ['ratings', 'quality']], ['other', ['demo']],
    ], 'Only the last item in the existing service group may be added');
    const activeItems = geometry.settingsGroups.flatMap(group => group.items).filter(item => item.active);
    assert.equal(activeItems.length, 1, 'Exactly one settings section must be active');
    assert.equal(activeItems[0].key, 'externalExecution');
    assert.equal(activeItems[0].label, externalLabel);
    assert.equal(activeItems[0].iconPath, serverIconPath, 'Use the current shared server icon');
    assert.equal(geometry.settingsGroups.find(group => group.key === 'service').items.at(-1).label, externalLabel);
    assert.equal(geometry.badLinks, 0);
    assert(geometry.externalCard, 'ExternalExecutionCard requires data-external-card');
    assert.equal(geometry.externalCard.fields, 0, 'OFF card must not show executor configuration fields');
    assert(geometry.externalCard.left >= -1 && geometry.externalCard.right <= 1, JSON.stringify({ test, geometry }));
    assert(geometry.externalCard.scrollWidth <= geometry.externalCard.clientWidth + 1, JSON.stringify({ test, geometry }));
    assert(geometry.externalCard.top >= -1 && geometry.externalCard.bottom <= geometry.height + 1, 'The off-state card must fit the first frame');
    assert.equal(await offToggle.count(), 1, 'One external execution switch is required');
    assert.equal(await offToggle.getAttribute('aria-checked'), 'false');
    if (width >= 1024) {
      assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
      assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
    } else {
      assert.equal(geometry.shellMinWidth, '0px', 'Preserve the existing mobile settings route override');
      results[results.length - 1].responsiveBehavior = 'Existing settings mobile route, hidden subnavigation and back header';
      if (geometry.scrollWidth > geometry.clientWidth + 1 || geometry.overflow.length) {
        results[results.length - 1].limitation = 'Inherited settings context has horizontal overflow; external card fits the viewport';
      }
    }
    if ((lang === 'ru' && theme === 'light' && [1440, 390].includes(width)) || (lang === 'en' && theme === 'dark' && width === 1440)) {
      const name = `S01-${lang}-${theme}-${width}.png`;
      await page.locator('.ea-screen').screenshot({ path: join(verification, name) });
      screenshots.push(name);
    }
  }
  for (const accent of ['#1677ff', '#e8590c']) {
    const test = { lang: 'ru', theme: 'light', width: 1440, accent };
    await open(test);
    const geometry = await page.evaluate(measure);
    assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
    results.push({ ...test, geometry });
  }
  await open({ lang: 'ru', theme: 'light', width: 1440 });
  await offToggle.click();
  assert.equal(await offToggle.getAttribute('aria-checked'), 'false', 'One-frame design must not activate an unreviewed state');
  await offToggle.focus();
  await page.keyboard.press('Space');
  assert.equal(await offToggle.getAttribute('aria-checked'), 'false');
  results.push({ check: 'Static OFF switch', click: 'remained OFF', keyboardSpace: 'remained OFF' });
  assert.equal(await page.locator('.settings-content button[type="submit"]').count(), 0, 'OFF state has no form to submit');
  results.push({ check: 'Dedicated settings navigation', group: 'service', position: 'last', icon: 'shared server', section: 'externalExecution' });

  // CSS review scaling at the same 1510px viewport; not a native browser zoom claim.
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  const zoomed = await page.evaluate(measure);
  assert.equal(zoomed.width, 2880);
  assert.equal(zoomed.overflow.length, 0, JSON.stringify(zoomed));
  results.push({ check: '200% CSS review scale at original viewport 1510', geometry: zoomed });
  const changedSinceBuild = manifest.sources.filter(source => createHash('sha256')
    .update(readFileSync(resolve(workspace, source.path))).digest('hex') !== source.sha256).map(source => source.path);
  assert.deepEqual(changedSinceBuild, [], 'Sources changed after build; repeat on the final revision');
  assert.equal(network.length, 0, JSON.stringify(network));
  assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log(JSON.stringify({ status: 'PASS', designVersion: manifest.designVersion,
    matrixCases: 16, additionalAccents: 2, browserErrors: errors.length, networkRequests: network.length,
    interactions: 'OFF switch click and keyboard remain in S01', screenshots, changedSinceBuild }));
} finally {
  writeFileSync(join(verification, 'browser-results.json'), JSON.stringify({
    designVersion: manifest.designVersion, scope: 'Static S01 only; no backend or integration verified',
    results, errors, network, screenshots,
  }, null, 2) + '\n');
  await browser.close();
}
