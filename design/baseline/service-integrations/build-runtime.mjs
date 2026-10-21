import { createRequire } from 'node:module';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const root = dirname(fileURLToPath(import.meta.url));
const workspace = resolve(root, '../../..');
const commonGit = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd: workspace, encoding: 'utf8' }).trim();
const dependencyRoot = process.env.BASELINE_NODE_MODULES || join(dirname(resolve(workspace, commonGit)), 'node_modules');
const require = createRequire(import.meta.url);
const { build } = require(require.resolve('esbuild', { paths: [workspace, dirname(dependencyRoot)] }));
const result = await build({
  absWorkingDir: workspace, entryPoints: [join(root, 'runtime.tsx')],
  outfile: join(root, 'generated/runtime.js'), bundle: true, format: 'iife',
  minify: true, jsx: 'automatic', write: false, metafile: true,
  nodePaths: [dependencyRoot], define: { 'process.env.NODE_ENV': '"production"', 'import.meta.env': '{}' },
  alias: {
    '@chatballs/ui': join(workspace, 'packages/ui/src/index.ts'),
    '@chatballs/shared': join(workspace, 'packages/shared/src/index.ts'),
    '@chatballs/contracts': join(workspace, 'packages/contracts/src/index.ts'),
  },
  loader: { '.svg': 'dataurl', '.png': 'dataurl', '.woff2': 'dataurl' },
  legalComments: 'none',
});
const { mkdirSync } = await import('node:fs');
mkdirSync(join(root, 'generated'), { recursive: true });
for (const file of result.outputFiles) {
  // A canvas frame, not the browser window, defines the preview's desktop width.
  // Preserve every product rule; only move width media queries to that container.
  const text = file.path.endsWith('.css')
    ? file.text.replace(/@media\s*\((max|min)-width:/g, '@container baseline ($1-width:')
    : file.text;
  writeFileSync(file.path, text);
}
const sources = Object.keys(result.metafile.inputs).filter(path => !path.includes('node_modules'));
writeFileSync(join(root, 'generated/sources.json'), JSON.stringify({ sources }));
console.log(`Built actual shared components and styles: ${sources.length} workspace sources.`);
