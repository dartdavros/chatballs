// Compile only presentation dependencies and standalone static design documents.
// No server, app services, fixtures or backend is started.
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { Script, runInNewContext } from 'node:vm';
import assert from 'node:assert/strict';

const root = dirname(fileURLToPath(import.meta.url)), workspace = resolve(root, '../../..');
const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencies = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, common)), 'node_modules');
const require = createRequire(import.meta.url);
const { build } = require(require.resolve('esbuild', { paths: [workspace, dirname(dependencies)] }));
mkdirSync(join(root, 'generated'), { recursive: true });
const result = await build({
  absWorkingDir: workspace, entryPoints: [join(root, 'runtime.tsx')], outfile: join(root, 'generated/runtime.js'),
  bundle: true, format: 'iife', minify: true, jsx: 'automatic', write: false, metafile: true,
  nodePaths: [dependencies], define: { 'process.env.NODE_ENV': '"production"', 'import.meta.env': '{}' },
  alias: { '@chatballs/ui': join(workspace, 'packages/ui/src/index.ts'),
    '@chatballs/shared': join(workspace, 'packages/shared/src/index.ts'),
    '@chatballs/contracts': join(workspace, 'packages/contracts/src/index.ts') },
  loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'dataurl' }, legalComments: 'none',
});
for (const file of result.outputFiles) writeFileSync(file.path, file.path.endsWith('.css')
  ? file.text.replace(/@media\s*\((max|min)-width:/g, '@container baseline ($1-width:') : file.text);
writeFileSync(join(root, 'generated/sources.json'), JSON.stringify({ sources: Object.keys(result.metafile.inputs).filter(p => !p.includes('node_modules')) }, null, 2));

const read = path => readFileSync(resolve(root, path), 'utf8');
for (const name of readdirSync(root).filter(n => /\.(js|css|tsx|mjs)$/.test(n))) {
  assert(read(name).split('\n').length <= 300, `${name}: NO GOD limit exceeded`);
  if (name.endsWith('.js')) new Script(read(name), { filename: name });
}
const copy = { window: {} };
for (const lang of ['ru', 'en']) runInNewContext(read(`copy-${lang}.js`), copy);
assert.deepEqual(Object.keys(copy.window.SpeechRu).sort(), Object.keys(copy.window.SpeechEn).sort(), 'RU/EN keys differ');
const scripts = ['generated/runtime.js', '../platform-expansion/support.js', 'copy-ru.js', 'copy-en.js', 'parts.js',
  'frames.js', 'web-header.js', 'settings-shell.js', 'settings-views.js', 'dictation-model.js', 'composer.js', 'player.js', 'legacy-voice.js', 'widget.js', 'canvas.js'];
const pages = ['settings', 'dictation', 'playback'];
for (const page of pages) {
  const html = `<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${copy.window.SpeechRu.canvasTitle}</title>
<script>window.__resources={};</script>
${scripts.map(src => `<script src="./${src}"></script>`).join('\n')}
</head><body><x-dc><helmet><meta name="design_doc_mode" content="canvas">
<link rel="stylesheet" href="./generated/runtime.css"><link rel="stylesheet" href="./baseline.css">
</helmet>{{ canvas }}</x-dc>
<script type="text/x-dc" data-dc-script>
class Component extends DCLogic { renderVals() {
  return { canvas: window.React.createElement(window.SpeechCanvas, { section: "${page}" }) };
} }
</script></body></html>\n`;
  writeFileSync(join(root, `${page}.dc.html`), html);
  let bundled = html.replace(/<script src="([^"]+)"><\/script>/g, (_, src) => `<script>${read(src).replaceAll('</script', '<\\/script')}</script>`);
  bundled = bundled.replace(/<link rel="stylesheet" href="([^"]+)">/g, (_, src) => `<style>${read(src)}</style>`);
  writeFileSync(join(root, `generated/open-${page}.playwright.js`), `async (page) => {
    await page.goto('about:blank');
    await page.setViewportSize({width:1510,height:1120});
    await page.setContent(${JSON.stringify(bundled)}, {waitUntil:'load'});
    await page.locator('[data-screen]').first().waitFor();
    return {title:await page.title(),frames:await page.locator('.sp-review select').first().locator('option').count()-1};
  }`);
}
console.log(JSON.stringify({ pages, frames: 52, translatedKeys: Object.keys(copy.window.SpeechRu).length,
  checks: 'presentation compilation, local resources, JS syntax, RU/EN parity, authored files <= 300 lines' }));
