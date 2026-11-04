// Repeatable verification of static artifacts in a clean Chrome profile.
// Native file URLs; no HTTP server, service stubs, accounts or speech requests.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import assert from 'node:assert/strict';

const root = dirname(fileURLToPath(import.meta.url)), workspace = resolve(root, '../../..');
const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencies = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, common)), 'node_modules');
const require = createRequire(import.meta.url);
const { chromium } = require(require.resolve('@playwright/test', { paths: [workspace, dirname(dependencies)] }));
const load = name => new Script(`(${readFileSync(join(root, name), 'utf8')})`, { filename: name }).runInNewContext();
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [], failures = [], network = [];
try {
  const page = await browser.newPage({ viewport: { width: 1510, height: 1120 } });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => failures.push(error.message));
  page.on('console', message => { if (message.type() === 'error') failures.push(message.text()); });
  page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  for (const name of ['settings', 'dictation', 'playback']) {
    await page.goto(new URL(`${name}.dc.html`, import.meta.url).href);
    await page.locator('[data-screen]').waitFor();
    for (const check of ['matrix', 'interactions', 'accessibility']) {
      const result = await load(`checks/${check}.playwright.js`)(page);
      results.push({ page: name, ...result });
      assert.equal(result.errors.length, 0, JSON.stringify(result));
      console.log(JSON.stringify({ page: name, check, measured: result.measured, verified: result.verified }));
    }
  }
  assert.equal(network.length, 0, JSON.stringify(network));
  assert.equal(failures.length, 0, JSON.stringify(failures));
  console.log('PASS: native file documents, no network calls or browser errors.');
} finally {
  mkdirSync(join(root, 'verification'), { recursive: true });
  writeFileSync(join(root, 'verification/browser-results.json'), JSON.stringify({ results, failures, network }, null, 2));
  await browser.close();
}
