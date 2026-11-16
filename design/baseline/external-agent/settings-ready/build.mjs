// Compile the single static S03. No application, backend or external service is started.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = dirname(fileURLToPath(import.meta.url)), workspace = resolve(root, '../../../..');
const require = createRequire(import.meta.url);
const common = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencies = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, common)), 'node_modules');
const { build } = require(require.resolve('esbuild', { paths: [workspace, dirname(dependencies)] }));
const read = path => readFileSync(resolve(root, path), 'utf8');
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const acceptedScreens = [
  ['settings-off', 'S01-5037b71a01f54b2b'],
  ['settings-unconfigured', 'S02-c8d1b152d7078f85'],
].map(([folder, expected]) => {
  const path = resolve(root, `../${folder}/generated/sources.json`), bytes = readFileSync(path);
  const baseline = JSON.parse(bytes);
  assert.equal(baseline.designVersion, expected, `Use the accepted ${folder} version`);
  for (const source of baseline.sources) {
    assert.equal(sha256(readFileSync(resolve(workspace, source.path))), source.sha256, `Accepted source changed: ${source.path}`);
  }
  return { folder, designVersion: expected, manifestSha256: sha256(bytes), sources: baseline.sources.length };
});
const aliases = {
  '@chatballs/ui': join(workspace, 'packages/ui/src/index.ts'),
  '@chatballs/shared': join(workspace, 'packages/shared/src/index.ts'),
  '@chatballs/contracts': join(workspace, 'packages/contracts/src/index.ts'),
};
const authored = readdirSync(root).filter(name => /\.(?:tsx?|m?js|css)$/.test(name));
const lineCounts = Object.fromEntries(authored.map(name => [name, read(name).split('\n').length]));
for (const [name, lines] of Object.entries(lineCounts)) {
  assert(lines <= 300, `${name}: authored-file limit exceeded (${lines})`);
  if (name.endsWith('.tsx')) assert(lines <= 180, `${name}: component limit exceeded (${lines})`);
}
mkdirSync(join(root, 'generated'), { recursive: true });
const result = await build({
  absWorkingDir: workspace, entryPoints: [join(root, 'runtime.tsx')],
  outfile: join(root, 'generated/runtime.js'), bundle: true, format: 'iife', minify: true,
  jsx: 'automatic', write: false, metafile: true, nodePaths: [dependencies], alias: aliases,
  define: { 'process.env.NODE_ENV': '"production"', 'import.meta.env': '{}' },
  loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'dataurl' }, legalComments: 'none',
});
let remappedMediaQueries = 0;
for (const file of result.outputFiles) {
  const content = file.path.endsWith('.css')
    ? file.text.replace(/@media\s*(\((?:max|min)-width\s*:[^{]+)\{/g, (_, query) => {
      remappedMediaQueries += 1; return `@container baseline ${query}{`;
    }) : file.text;
  writeFileSync(file.path, content);
}
const dictionary = await build({
  entryPoints: [join(root, 'copy.ts')], bundle: true, format: 'cjs', platform: 'node',
  write: false, nodePaths: [dependencies], alias: aliases, legalComments: 'none',
});
const module = { exports: {} };
runInNewContext(dictionary.outputFiles[0].text, {
  module, exports: module.exports, URLSearchParams,
  window: { location: { search: '?lang=ru' } }, location: { search: '?lang=ru' },
});
const copy = module.exports.copy;
assert(copy?.ru && copy?.en, 'copy.ts must export copy.ru and copy.en');
const keys = Object.keys(copy.ru).sort();
assert.deepEqual(keys, Object.keys(copy.en).sort(), 'RU/EN keys differ');
for (const lang of ['ru', 'en']) for (const [key, value] of Object.entries(copy[lang])) {
  assert(typeof value === 'string' && value.trim(), `${lang}.${key}: missing text`);
}
for (const name of authored.filter(name => /\.tsx?$/.test(name))) {
  for (const match of read(name).matchAll(/\btx\(\s*["']([^"']+)["']/g)) {
    assert(Object.hasOwn(copy.ru, match[1]), `${name}: missing copy key ${match[1]}`);
  }
}
const html = `<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Внешнее исполнение · S03 · Дизайн</title>
<script>
window.__resources = {};
const designLanguage = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ru';
localStorage.setItem('chatballs.language', designLanguage);
document.documentElement.lang = designLanguage;
</script>
<script src="./generated/runtime.js"></script>
<script src="../../platform-expansion/support.js"></script>
</head><body><x-dc><helmet>
<meta name="design_doc_mode" content="canvas">
<link rel="stylesheet" href="./generated/runtime.css">
</helmet>{{ canvas }}</x-dc>
<script type="text/x-dc" data-dc-script>
class Component extends DCLogic {
  renderVals() { return { canvas: window.React.createElement(window.ExternalReadyCanvas) }; }
}
</script></body></html>
`;
writeFileSync(join(root, 'settings.dc.html'), html);
const sources = new Set(Object.keys(result.metafile.inputs)
  .filter(path => !path.includes('node_modules') && !path.startsWith('<'))
  .map(path => resolve(workspace, path)));
for (const name of authored) sources.add(join(root, name));
sources.add(resolve(root, '../../platform-expansion/support.js'));
const hashes = [...sources].map(path => ({
  path: relative(workspace, path).replaceAll('\\', '/'), sha256: sha256(readFileSync(path)),
})).sort((a, b) => a.path.localeCompare(b.path));
const manifest = {
  designVersion: `S03-${sha256(JSON.stringify(hashes)).slice(0, 16)}`,
  page: 'settings.dc.html', screens: ['S03'],
  scope: 'Static connection-readiness design only; no service, credential, agent execution or delivery verified',
  acceptedScreens, sources: hashes, authoredLineCounts: lineCounts, translatedKeys: keys, remappedMediaQueries,
};
writeFileSync(join(root, 'generated/sources.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({ designVersion: manifest.designVersion, screens: 1, sourceFiles: hashes.length,
  translatedKeys: keys.length, authoredMaxLines: Math.max(...Object.values(lineCounts)), remappedMediaQueries,
  acceptedScreens: acceptedScreens.map(item => ({ version: item.designVersion, sources: item.sources, unchanged: true })),
  checks: 'presentation compilation, RU/EN keys, source hashes, file/component sizes' }));
