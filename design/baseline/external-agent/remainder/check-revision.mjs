// Targeted native-file QA for the requested revision; the archived full matrix report is untouched.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { acceptedState, sha } from './scripts/build-support.mjs';
import { measure } from './scripts/measure.mjs';
import { validate } from './scripts/assert-screen.mjs';
import { revisionGeometry, validateRevisionGeometry, settleModal, checkHelpTriggers, expectedHelpTopics,
  checkTemplateLinks, checkBindings } from './scripts/revision-checks.mjs';
import { qualityGeometry, validateQualityGeometry, checkActionLinkQuality, checkNativeCopy } from './scripts/quality-checks.mjs';

const root = dirname(fileURLToPath(import.meta.url)), workspace = resolve(root, '../../../..');
const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencies = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, common)), 'node_modules');
const require = createRequire(import.meta.url);
const { chromium } = require(require.resolve('@playwright/test', { paths: [workspace, dirname(dependencies)] }));
const manifest = JSON.parse(readFileSync(join(root, 'generated/sources.json'), 'utf8'));
const accepted = acceptedState(root, workspace);
assert.deepEqual(manifest.acceptedScreens, accepted, 'Accepted source manifests must match the build');
const saveProgressOnly = process.argv.includes('--save-progress-only');
const priorDirectory = 'verification/history/REST-54b67c04753798a0';
let priorVerification = null;
if (saveProgressOnly) {
  const prior = JSON.parse(readFileSync(join(root, priorDirectory, 'browser-results.json')));
  const priorSources = JSON.parse(readFileSync(join(root, priorDirectory, 'sources.json')));
  assert.equal(prior.status, 'PASS'); assert.equal(prior.designVersion, priorSources.designVersion);
  const oldHashes = new Map(priorSources.sources.map(source => [source.path, source.sha256]));
  const changes = manifest.sources.filter(source => oldHashes.get(source.path) !== source.sha256).map(source => source.path);
  const prefix = 'design/baseline/external-agent/remainder/';
  assert.deepEqual(changes.sort(), [prefix + 'check-revision.mjs', prefix + 'settings/state-layout.css'].sort(), 'Only the S34 busy style and QA filter may differ');
  priorVerification = { path: `${priorDirectory}/browser-results.json`, designVersion: prior.designVersion, scope: prior.scope, changes };
}
const settings = manifest.screens.filter(c => c.group === 'settings' && (!saveProgressOnly || c.id === 'S34')); assert.equal(settings.length, saveProgressOnly ? 1 : 22);
const representativeIds = saveProgressOnly ? ['S34'] : ['S20', 'S24', 'S32', 'S33', 'S34', 'S35', 'S38', 'S39', 'S72'];
const otherIds = saveProgressOnly ? [] : ['S08', 'S11', 'S14', 'S70', 'S41'];
const output = join(root, 'verification', 'revision'); mkdirSync(output, { recursive: true });
const results = [], failures = [], errors = [], network = [], screenshots = new Set();
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage(); page.setDefaultTimeout(30000);
let current = '', status = 'RUNNING';
page.on('pageerror', error => errors.push({ id: current, message: error.message }));
page.on('console', message => { if (message.type() === 'error') errors.push({ id: current, message: message.text() }); });
page.on('request', request => { if (/^https?:/.test(request.url())) network.push({ id: current, url: request.url() }); });
const caseFor = id => { const c = manifest.screens.find(item => item.id === id); assert(c, `Missing case ${id}`); return c; };
const capture = async name => {
  const file = `${name}.png`; if (screenshots.has(file)) return;
  await page.screenshot({ path: join(output, file), timeout: 45000 }); screenshots.add(file);
};
const contextName = test => `${current}-${test.lang}-${test.theme}-${test.width}`;
async function open(c, test) {
  current = c.id; await page.setViewportSize({ width: test.width, height: 980 });
  const url = new URL(`${c.id}.dc.html`, import.meta.url);
  url.search = new URLSearchParams({ screen: c.id, embed: '1', lang: test.lang, theme: test.theme, width: String(test.width), accent: '#0f9b8e' });
  await page.goto(url.href, { waitUntil: 'load' }); await page.locator('.ea-screen').waitFor();
  await page.evaluate(() => document.fonts.ready);
  if (c.modal) await settleModal(page);
  assert.equal(await page.locator('.ea-screen').count(), 1);
}
async function run(c, test, phase, operation) {
  current = c.id;
  try {
    const detail = await operation(); results.push({ id: c.id, ...test, phase, ...detail }); return true;
  } catch (error) {
    failures.push({ id: c.id, ...test, phase, error: error.message });
    await capture(`FAIL-${contextName(test)}-${phase}`).catch(() => {}); return false;
  }
}
async function inspect(c, test, phase, image = false) {
  return run(c, test, phase, async () => {
    await open(c, test);
    const geometry = await page.evaluate(measure); validate(geometry, c, test);
    const revision = await page.evaluate(revisionGeometry); validateRevisionGeometry(revision, c);
    const quality = await page.evaluate(qualityGeometry); validateQualityGeometry(quality, c);
    if (c.id === 'S34') {
      const busyStyle = await page.locator('footer.external-save-footer button').evaluate(button => {
        const style = getComputedStyle(button); return { opacity: Number(style.opacity), color: style.color };
      });
      assert.equal(busyStyle.opacity, 1, 'Progress remains visible while the button is disabled');
      assert.equal(busyStyle.color, 'rgb(255, 255, 255)', 'Use the existing busy-button foreground');
    }
    if (image) {
      await capture(contextName(test));
      if (['S33', 'S34', 'S35'].includes(c.id)) {
        await page.locator('footer.external-save-footer').scrollIntoViewIfNeeded(); await capture(`${contextName(test)}-footer`);
      }
    }
    return { geometry, revision, quality };
  });
}
const ruDesktop = { lang: 'ru', theme: 'light', width: 1440 };
try {
  for (const c of settings) await inspect(c, ruDesktop, 'settings-desktop', representativeIds.includes(c.id));
  console.log(JSON.stringify({ phase: 'settings-desktop', checked: settings.length, failures: failures.length }));
  for (const lang of ['ru', 'en']) for (const theme of ['light', 'dark']) for (const width of [1440, 320]) {
    for (const id of representativeIds) {
      await inspect(caseFor(id), { lang, theme, width }, 'settings-matrix', lang === 'en' && theme === 'dark' && width === 320);
    }
  }
  for (const id of otherIds) for (const width of [1440, 320]) {
    const test = { ...ruDesktop, width }, c = caseFor(id);
    const passed = await inspect(c, test, 'changed-basics', true);
    if (passed) await run(c, test, 'changed-help', async () => ({ help: await checkHelpTriggers(page) }));
  }
  const interactionTests = saveProgressOnly ? [] : [ruDesktop, { lang: 'en', theme: 'dark', width: 320 }];
  for (const test of interactionTests) {
    const c = caseFor('S20');
    await run(c, test, 'help-and-message-previews', async () => {
      await open(c, test); const save = name => capture(`${contextName(test)}-${name}`);
      const help = await checkHelpTriggers(page, save, expectedHelpTopics);
      const previews = await checkTemplateLinks(page, save);
      const linkAndTable = await checkActionLinkQuality(page, save); return { help, previews, linkAndTable };
    });
    await run(c, test, 'binding-interactions', async () => {
      await open(c, test); const bindings = await checkBindings(page, name => capture(`${contextName(test)}-${name}`));
      await page.reload({ waitUntil: 'load' }); await page.locator('[data-agent-bindings]').waitFor();
      assert.equal(await page.locator('[data-binding-row]').count(), 2, 'Reload restores document defaults without persistence');
      return { bindings };
    });
    await run(caseFor('S24'), test, 'native-key-copy', async () => {
      await open(caseFor('S24'), test);
      return { copy: await checkNativeCopy(page, name => capture(`${contextName(test)}-${name}`)) };
    });
  }
  assert.deepEqual(failures, [], 'Targeted revision checks'); assert.deepEqual(errors, [], 'Browser errors'); assert.deepEqual(network, [], 'No HTTP(S) requests');
  const changed = manifest.sources.filter(source => sha(readFileSync(resolve(workspace, source.path))) !== source.sha256).map(source => source.path);
  assert.deepEqual(changed, [], 'Rebuild before checking modified sources'); assert.deepEqual(acceptedState(root, workspace), accepted);
  status = 'PASS';
  console.log(JSON.stringify({ status, designVersion: manifest.designVersion, scope: 'targeted-revision',
    layoutChecks: results.filter(r => r.geometry).length, interactionChecks: results.filter(r => !r.geometry).length,
    testedIds: [...new Set(results.map(r => r.id))], errors: errors.length, network: network.length, screenshots: screenshots.size }));
} catch (error) {
  status = 'FAIL'; console.log(JSON.stringify({ status, error: error.message, failures, errors, network })); process.exitCode = 1;
} finally {
  writeFileSync(join(root, 'verification', 'revision-results.json'), JSON.stringify({ status, designVersion: manifest.designVersion,
    priorVerification, scope: { kind: saveProgressOnly ? 'S34-busy-style-followup' : 'targeted-revision', settingsDesktopIds: settings.map(c => c.id), settingsMatrixIds: representativeIds,
      matrixLanguages: ['ru', 'en'], matrixThemes: ['light', 'dark'], matrixWidths: [1440, 320], changedBasicsIds: otherIds,
      interactionIds: saveProgressOnly ? [] : ['S20', 'S24', ...otherIds], features: saveProgressOnly ? ['S34 visible busy button'] : ['DS binding modals', 'Native clipboard feedback and bare copy icon', 'Compact save footer', 'Framed load error', 'Feature state spacing', 'Right-aligned switch tables', 'Common action links', 'Contextual help and message previews'],
      note: 'Only listed revision scenarios were rechecked; the historical full report was not overwritten.' },
    testedIds: [...new Set([...results, ...failures].map(r => r.id))], accepted, results, failures, errors, network, screenshots: [...screenshots] }, null, 2) + '\n');
  await browser.close();
}
