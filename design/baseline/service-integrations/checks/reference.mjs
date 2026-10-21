// Opens the unmodified reference document in Skaro's isolated browser, without a server.
import { readFileSync, writeFileSync } from 'node:fs';
const root = new URL('../', import.meta.url);
const reference = new URL('../../Chatballs Baseline v2/Настройки Baseline.dc.html', import.meta.url);
let html = readFileSync(reference, 'utf8');
const runtime = readFileSync(new URL('generated/runtime.js', root), 'utf8');
html = html.replace('<head>', `<head><script>window.__resources={};${runtime.replaceAll('</script', '<\\/script')}</script>`);
html = html.replace(/<script src="([^"]+)"><\/script>/g, (_, src) =>
  `<script>${readFileSync(new URL(src, reference), 'utf8').replaceAll('</script', '<\\/script')}</script>`);
html = html.replace(/src="(assets\/[^"]+)"/g, (_, src) => {
  const mime = src.endsWith('.svg') ? 'image/svg+xml' : 'image/png';
  return `src="data:${mime};base64,${readFileSync(new URL(src, reference)).toString('base64')}"`;
});
writeFileSync(new URL('generated/open-reference.playwright.js', root), `async(page)=>{
  await page.goto('about:blank');
  await page.setViewportSize({width:1520,height:1100});
  await page.setContent(${JSON.stringify(html)}, {waitUntil:'load'});
  await page.locator('#n4').waitFor();
  return {reference:'Настройки Baseline.dc.html',frame:'n4'};
}`);
