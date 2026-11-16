// Build only presentation resources for the standalone design document.
// This command starts no server, API, application environment or external service.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const root = dirname(fileURLToPath(import.meta.url));
const workspace = resolve(root, "../../..");
const common = execFileSync("git", ["rev-parse", "--git-common-dir"], {
  cwd: workspace, encoding: "utf8",
}).trim();
const dependencies = process.env.BASELINE_NODE_MODULES
  || join(dirname(resolve(workspace, common)), "node_modules");
const require = createRequire(import.meta.url);
const { build } = require(require.resolve("esbuild", {
  paths: [workspace, dirname(dependencies)],
}));
const read = path => readFileSync(resolve(root, path), "utf8");
const sha256 = bytes => createHash("sha256").update(bytes).digest("hex");
const normalize = path => path.replaceAll("\\", "/");
const aliases = {
  "@chatballs/ui": join(workspace, "packages/ui/src/index.ts"),
  "@chatballs/shared": join(workspace, "packages/shared/src/index.ts"),
  "@chatballs/contracts": join(workspace, "packages/contracts/src/index.ts"),
};
const authored = readdirSync(root).filter(name => /\.(?:tsx?|m?js|css)$/.test(name));
const lineCounts = Object.fromEntries(authored.map(name => [name, read(name).split("\n").length]));
for (const [name, lines] of Object.entries(lineCounts)) {
  assert(lines <= 300, `${name}: ${lines} lines exceed the authored-file limit`);
}
mkdirSync(join(root, "generated"), { recursive: true });
const result = await build({
  absWorkingDir: workspace,
  entryPoints: [join(root, "runtime.tsx")],
  outfile: join(root, "generated/runtime.js"),
  bundle: true, format: "iife", minify: true, jsx: "automatic",
  write: false, metafile: true, nodePaths: [dependencies], alias: aliases,
  define: { "process.env.NODE_ENV": '"production"', "import.meta.env": "{}" },
  loader: { ".svg": "dataurl", ".png": "dataurl", ".woff2": "dataurl" },
  legalComments: "none",
});
// Match application breakpoints to the design frame rather than the review canvas.
let remappedMediaQueries = 0;
for (const file of result.outputFiles) {
  const text = file.path.endsWith(".css")
    ? file.text.replace(/@media\s*(\((?:max|min)-width\s*:[^{]+)\{/g, (_, query) => {
      remappedMediaQueries += 1;
      return `@container baseline ${query}{`;
    }) : file.text;
  writeFileSync(file.path, text);
}

// Compile the actual new dictionary in memory to verify its two catalogs.
const dictionaryBundle = await build({
  absWorkingDir: workspace, entryPoints: [join(root, "copy.ts")],
  bundle: true, format: "cjs", platform: "node", write: false,
  nodePaths: [dependencies], alias: aliases, legalComments: "none",
});
const module = { exports: {} };
runInNewContext(dictionaryBundle.outputFiles[0].text, {
  module, exports: module.exports, URLSearchParams,
  window: { location: { search: "?lang=ru" } }, location: { search: "?lang=ru" },
}, { filename: "copy.ts (compiled for catalog verification)" });
const dictionaries = module.exports.copy;
assert(dictionaries?.ru && dictionaries?.en, "copy.ts must export copy.ru and copy.en");
const russianKeys = Object.keys(dictionaries.ru).sort();
assert.deepEqual(russianKeys, Object.keys(dictionaries.en).sort(), "RU/EN keys differ");
for (const language of ["ru", "en"]) {
  for (const [key, value] of Object.entries(dictionaries[language])) {
    assert.equal(typeof value, "string", `${language}.${key}: expected a string`);
    assert(value.trim(), `${language}.${key}: empty translation`);
  }
}
const referencedKeys = new Set();
for (const name of authored.filter(name => /\.tsx?$/.test(name))) {
  for (const match of read(name).matchAll(/\btx\(\s*["']([^"']+)["']/g)) {
    referencedKeys.add(match[1]);
    assert(Object.hasOwn(dictionaries.ru, match[1]), `${name}: missing key ${match[1]}`);
  }
}

const html = `<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Внешний агент · A01 · Дизайн</title>
<script>
window.__resources = {};
const language = new URLSearchParams(location.search).get("lang") === "en" ? "en" : "ru";
localStorage.setItem("chatballs.language", language);
document.documentElement.lang = language;
</script>
<script src="./generated/runtime.js"></script>
<script src="../platform-expansion/support.js"></script>
</head><body><x-dc><helmet>
<meta name="design_doc_mode" content="canvas">
<link rel="stylesheet" href="./generated/runtime.css">
<link rel="stylesheet" href="./baseline.css">
</helmet>{{ canvas }}</x-dc>
<script type="text/x-dc" data-dc-script>
class Component extends DCLogic {
  renderVals() { return { canvas: window.React.createElement(window.ExternalAgentCanvas) }; }
}
</script></body></html>
`;
writeFileSync(join(root, "agent.dc.html"), html);

const sourcePaths = new Set(Object.keys(result.metafile.inputs)
  .filter(path => !path.includes("node_modules") && !path.startsWith("<"))
  .map(path => resolve(workspace, path)));
for (const name of authored) sourcePaths.add(join(root, name));
sourcePaths.add(resolve(root, "../platform-expansion/support.js"));
const sources = [...sourcePaths].map(path => ({
  path: normalize(relative(workspace, path)),
  sha256: sha256(readFileSync(path)),
})).sort((a, b) => a.path.localeCompare(b.path));
const version = sha256(JSON.stringify(sources)).slice(0, 16);
const manifest = {
  designVersion: `A01-${version}`,
  page: "agent.dc.html", screens: ["A01"],
  runtime: "static presentation; no backend or external integration verification",
  sources, authoredLineCounts: lineCounts,
  translatedKeys: russianKeys, referencedKeys: [...referencedKeys].sort(),
  remappedMediaQueries,
};
writeFileSync(join(root, "generated/sources.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(JSON.stringify({
  designVersion: manifest.designVersion, pages: 1, frames: 1,
  sourceFiles: sources.length, translatedKeys: russianKeys.length,
  authoredMinLines: Math.min(...Object.values(lineCounts)),
  authoredMaxLines: Math.max(...Object.values(lineCounts)),
  remappedMediaQueries,
  checks: "presentation compilation; source hashes; RU/EN parity; referenced keys; authored files <=300 lines",
}));
