// Builds a static design document for browser tools that cannot open file://.
// No server, API, test data or application runtime is created.
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import assert from 'node:assert/strict';

const root = new URL('./', import.meta.url);
const pages = ['connections', 'editor', 'settings', 'journey'];
const read = url => readFileSync(url, 'utf8');
// All entry points share the current baseline instead of opening rejected editors.
const canonical = read(new URL('journey.dc.html', root));
for (const [name, initialFrame] of [['connections','J10'],['editor','X01'],['settings','Y15']]) {
  writeFileSync(new URL(`${name}.dc.html`, root), canonical.replace('{ page: "journey" }', `{ page: "journey", initialFrame: "${initialFrame}" }`));
}
const ids = [];
for (const name of readdirSync(root)) {
  if (!name.endsWith('.js')) continue;
  const source = read(new URL(name, root));
  new Script(source, { filename: name });
  assert(source.split('\n').length <= 300, `${name}: split responsibilities before adding more frames`);
  ids.push(...[...source.matchAll(/(?:frame|auth|shell)\('([A-Z]\d{2})'/g)].map(m => m[1]));
}
assert.equal(new Set(ids).size, ids.length, 'Frame identifiers must be unique');
const asset = (name, mime) => `data:${mime};base64,${readFileSync(new URL(`../platform-expansion/assets/${name}`, root)).toString('base64')}`;

function bundle(name) {
  assert(pages.includes(name), 'Unknown baseline page');
  let html = read(new URL(`${name}.dc.html`, root));
  assert(html.includes('<x-dc>') && html.includes('content="canvas"'), 'Expected canvas x-dc');
  assert(html.includes('support.js'), 'Expected existing support runtime');
  html = html.replace(/<script src="([^"]+)"><\/script>/g, (_, path) => {
    let source = read(new URL(path, root));
    source = source.replaceAll('../platform-expansion/assets/logo-sunset.svg', asset('logo-sunset.svg', 'image/svg+xml'));
    source = source.replaceAll('../platform-expansion/assets/av-4.png', asset('av-4.png', 'image/png'));
    source = source.replace(/\.\/assets\/logos\/[a-z-]+\.svg/g, path => `data:image/svg+xml;base64,${readFileSync(new URL(path, root)).toString('base64')}`);
    return `<script>${source.replaceAll('</script', '<\\/script')}</script>`;
  });
  html = html.replace(/<link rel="stylesheet" href="([^"]+)">/g, (_, path) => `<style>${read(new URL(path, root))}</style>`);
  return html.replace('<head>', '<head>\n<script>window.__resources = {};</script>');
}

const bundled = Object.fromEntries(pages.map(name => [name, bundle(name)]));
if (process.argv[2] === '--preview') {
  const name = process.argv[3] || 'journey';
  assert(pages.includes(name));
  writeFileSync(new URL('generated/open.playwright.js', root), `async (page) => {
    await page.goto('about:blank');
    await page.setViewportSize({width: 1510, height: 1150});
    await page.setContent(${JSON.stringify(bundled[name])}, {waitUntil: 'load'});
    await page.locator('.si-screen').first().waitFor();
    return {title: await page.title(), frames: await page.locator('.si-review select').first().locator('option').count()};
  }`);
  console.log('Prepared generated/open.playwright.js (static document, no server).');
} else if (process.argv[2] === '--bundle') {
  const name = process.argv[3];
  assert(pages.includes(name), 'Usage: --bundle connections|editor|settings|journey');
  process.stdout.write(JSON.stringify({ page: name, html: bundled[name] }));
} else {
  console.log(JSON.stringify({ pages, frameCount: ids.length, frames: ids.sort(), checked: 'JavaScript syntax, unique IDs, local resources, x-dc/canvas, file size', root: fileURLToPath(root) }, null, 2));
}
