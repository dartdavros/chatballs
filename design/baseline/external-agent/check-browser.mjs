// Check the static design in installed Chrome using native file URLs.
// No HTTP server, interception, fixtures, backend or external requests.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const workspace = resolve(root, "../../..");
const common = execFileSync("git", ["rev-parse", "--git-common-dir"], {
  cwd: workspace, encoding: "utf8",
}).trim();
const dependencies = process.env.BASELINE_NODE_MODULES
  || join(dirname(resolve(workspace, common)), "node_modules");
const require = createRequire(import.meta.url);
const { chromium } = require(require.resolve("@playwright/test", {
  paths: [workspace, dirname(dependencies)],
}));
const manifest = JSON.parse(readFileSync(join(root, "generated/sources.json"), "utf8"));
const verification = join(root, "verification");
mkdirSync(verification, { recursive: true });
const results = [], errors = [], network = [], screenshots = [];
const browser = await chromium.launch({ channel: "chrome", headless: true });
const measure = () => {
  const screen = document.querySelector(".ea-screen[data-screen='A01']");
  const bounds = screen.getBoundingClientRect();
  const shell = screen.querySelector(".hub-shell");
  const visible = element => {
    const style = getComputedStyle(element), rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width && rect.height;
  };
  const overflow = [];
  for (const element of screen.querySelectorAll("*")) {
    if (!visible(element)) continue;
    const rect = element.getBoundingClientRect();
    if (rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1) continue;
    let clipped = false;
    for (let parent = element.parentElement; parent && parent !== screen; parent = parent.parentElement) {
      if (/auto|scroll|hidden|clip/.test(getComputedStyle(parent).overflowX)) {
        clipped = true;
        break;
      }
    }
    if (!clipped) overflow.push({
      tag: element.tagName, className: String(element.className).slice(0, 100),
      left: Math.round(rect.left - bounds.left), right: Math.round(rect.right - bounds.right),
      text: element.textContent.trim().slice(0, 80),
    });
  }
  const saveButtons = [...screen.querySelectorAll("button")]
    .filter(button => /^(сохранить|save)$/i.test(button.textContent.trim()))
    .map(button => ({ text: button.textContent.trim(), disabled: button.disabled }));
  return {
    width: Math.round(bounds.width), height: Math.round(bounds.height),
    clientWidth: screen.clientWidth, scrollWidth: screen.scrollWidth,
    shellWidth: Math.round(shell.getBoundingClientRect().width),
    shellMinWidth: parseFloat(getComputedStyle(shell).minWidth),
    fields: screen.querySelectorAll("input,textarea,button.select-box").length,
    cards: screen.querySelectorAll(".agent-card").length,
    overflow, saveButtons,
    badLinks: [...screen.querySelectorAll("a")]
      .filter(link => link.getAttribute("href") === "#").map(link => link.textContent),
    lang: document.documentElement.lang, theme: document.documentElement.dataset.theme,
  };
};

try {
  const page = await browser.newPage({ viewport: { width: 1510, height: 1120 } });
  page.setDefaultTimeout(10000);
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("request", request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  const open = async ({ lang, theme, width, accent = "#0f9b8e" }) => {
    const url = new URL("agent.dc.html", import.meta.url);
    url.search = new URLSearchParams({ lang, theme, width: String(width), height: "980", accent });
    await page.goto(url.href, { waitUntil: "load" });
    await page.locator(".ea-screen[data-screen='A01']").waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(80);
    assert.equal(await page.locator("[data-screen]").count(), 1, "Only A01 may be displayed");
  };
  for (const lang of ["ru", "en"]) {
    for (const theme of ["light", "dark"]) {
      for (const width of [1440, 1024, 390, 320]) {
        const test = { lang, theme, width };
        await open(test);
        const geometry = await page.evaluate(measure);
        results.push({ ...test, geometry });
        assert.equal(geometry.width, width, JSON.stringify({ test, geometry }));
        assert.equal(geometry.height, 980, JSON.stringify({ test, geometry }));
        assert.equal(geometry.lang, lang, "Application and new strings must use the selected language");
        assert.equal(geometry.theme, theme, "Theme must follow the review selection");
        if (width >= 1024) {
          assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, overflow: geometry.overflow }));
          assert(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify({ test, geometry }));
        } else {
          // The current non-chat application intentionally retains a 1024px desktop shell.
          assert(geometry.shellMinWidth >= 1024 && geometry.shellWidth >= 1024,
            "Preserve the application's existing desktop minimum width");
          assert(geometry.scrollWidth >= 1024 && geometry.scrollWidth > geometry.clientWidth,
            "Narrow frames must expose the existing horizontal overflow, not invented mobile UI");
          results.at(-1).limitation = "Existing non-chat desktop layout; horizontal scrolling below 1024px";
        }
        assert(geometry.saveButtons.every(button => button.disabled), "Static design must not simulate saving");
        assert.equal(geometry.badLinks.length, 0, "Actions must use buttons instead of href=#");
        if ((lang === "ru" && theme === "light" && [1440, 390].includes(width))
          || (lang === "en" && theme === "dark" && width === 1440)) {
          const filename = `A01-${lang}-${theme}-${width}.png`;
          await page.locator(".ea-screen").screenshot({ path: join(verification, filename) });
          screenshots.push(filename);
        }
      }
    }
  }
  for (const accent of ["#1677ff", "#e8590c"]) {
    const test = { lang: "ru", theme: "light", width: 1440, accent };
    await open(test);
    const geometry = await page.evaluate(measure);
    results.push({ ...test, geometry });
    assert.equal(geometry.overflow.length, 0, JSON.stringify({ test, geometry }));
  }
  await open({ lang: "ru", theme: "light", width: 1440 });
  const select = page.locator(".ea-screen .select-like button.select-box:enabled").first();
  assert(await select.count(), "At least one real shared SelectField is required");
  await select.click();
  await page.locator(".app-dropdown:visible").first().waitFor();
  await page.keyboard.press("Escape");
  await page.locator(".app-dropdown:visible").waitFor({ state: "hidden" });
  await select.focus();
  await page.keyboard.press("Enter");
  await page.locator(".app-dropdown:visible").first().waitFor();
  await page.keyboard.press("Escape");
  await page.locator(".app-dropdown:visible").waitFor({ state: "hidden" });
  results.push({ check: "shared SelectField", click: "opened", enter: "opened", escape: "closed" });

  for (const [lang, label, inheritedLabel] of [
    ["ru", "Расшифровка голосовых", "Как у ответов"],
    ["en", "Voice transcription", "Same as answers"],
  ]) {
    await open({ lang, theme: "light", width: 1440 });
    const transcription = page.locator(".ea-screen").getByRole("button", { name: label, exact: true });
    await transcription.click();
    const menu = page.locator(".app-dropdown:visible");
    await menu.waitFor();
    const options = await menu.locator(".ant-dropdown-menu-item").allTextContents();
    assert(!options.some(option => option.includes(inheritedLabel)),
      "External replies cannot be inherited as a speech transcription provider");
    assert(options.some(option => option.includes("SpeechKit")), "The independent STT provider must remain available");
    await page.keyboard.press("Escape");
    await menu.waitFor({ state: "hidden" });
    results.push({ check: "independent transcription provider", lang, options });
  }
  await open({ lang: "ru", theme: "light", width: 1440 });
  const assistance = page.locator(".ea-screen .agent-assistance");
  const assistanceToggle = assistance.locator("button[role='switch']:enabled");
  const assistanceBefore = await assistanceToggle.getAttribute("aria-checked");
  await assistanceToggle.click();
  await page.waitForTimeout(100);
  assert.equal(await assistanceToggle.getAttribute("aria-checked"), assistanceBefore,
    "The static context guard must prevent the assistance state from changing");
  assert(!/\bis-(?:saving|error)\b/.test(await assistance.getAttribute("class")),
    "The static context guard must prevent the product save/error state machine");
  results.push({ check: "static assistance context", state: assistanceBefore, saveOrError: false });

  const scroll = page.locator(".ea-screen .hub-scroll");
  assert.equal(await scroll.count(), 1, "Use the existing product content scroll region");
  const scrollPosition = await scroll.evaluate(element => {
    const previous = element.scrollTop;
    element.scrollTop = element.scrollHeight;
    return { previous, current: element.scrollTop, maximum: element.scrollHeight - element.clientHeight };
  });
  const bottomScreenshot = "A01-ru-light-1440-bottom.png";
  await page.locator(".ea-screen").screenshot({ path: join(verification, bottomScreenshot) });
  screenshots.push(bottomScreenshot);
  results.push({ check: "desktop content bottom", ...scrollPosition, screenshot: bottomScreenshot });
  await scroll.evaluate((element, previous) => { element.scrollTop = previous; }, scrollPosition.previous);

  // CSS review scaling at the original viewport; this is not a mobile adaptation.
  await page.evaluate(() => { document.body.style.zoom = "2"; });
  const zoomed = await page.evaluate(measure);
  results.push({ check: "200% CSS review scale", viewportWidth: 1510, geometry: zoomed });
  assert.equal(zoomed.width, 2880);
  assert.equal(zoomed.overflow.length, 0, JSON.stringify(zoomed));
  assert.equal(errors.length, 0, JSON.stringify(errors));
  assert.equal(network.length, 0, JSON.stringify(network));
  console.log(JSON.stringify({
    status: "PASS", designVersion: manifest.designVersion,
    matrixCases: 16, additionalAccents: 2, interactions: "shared select click/Enter/Esc",
    screenshots, networkRequests: network.length, browserErrors: errors.length,
  }));
} finally {
  writeFileSync(join(verification, "browser-results.json"), JSON.stringify({
    designVersion: manifest.designVersion,
    scope: "Static A01 design only; no working backend or external integration verified",
    limitation: "Current non-chat product pages retain a 1024px desktop shell; 320/390px frames horizontally scroll",
    results, errors, network, screenshots,
  }, null, 2) + "\n");
  await browser.close();
}
