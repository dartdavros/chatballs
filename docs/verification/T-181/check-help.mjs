import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import * as yaml from "js-yaml";

const source = (key, path) => process.env[key]
  ? Buffer.from(process.env[key], "base64").toString("utf8")
  : readFileSync(new URL(path, import.meta.url), "utf8");
const loader = source("CHATBALLS_SITE_LOADER_BASE64", "../../../apps/backend/chatballs/webchat/loader_assets/site_events.js");
const articles = yaml.load(source("CHATBALLS_SITE_HELP_BASE64", "../../portal-curation/articles/sobytiya-sayta.yml")).articles;
const fence = String.fromCharCode(96).repeat(3);

function browser() {
  let now = 1000000, next = 0;
  const timers = new Map(), messages = [];
  const context = {
    Date: { now: () => now }, TextEncoder,
    setTimeout: (callback, delay) => { timers.set(++next, { callback, at: now + delay }); return next; },
    clearTimeout: id => timers.delete(id),
    widgetKey: "PUBLIC_WIDGET_KEY", instanceId: "help-example", origin: "https://widget.example",
    frame: { contentWindow: { postMessage: message => messages.push(message) } },
    renderSiteInvitation() {}, setOpen() {},
  };
  context.window = context;
  return { context, messages, advance(ms) {
    now += ms;
    for (const [id, timer] of timers) if (timer.at <= now) { timers.delete(id); timer.callback(); }
  } };
}

assert.deepEqual(articles.map(article => article.locale).sort(), ["en", "ru"]);
for (const article of articles) {
  const blocks = [...article.content.matchAll(new RegExp(fence + "javascript\\r?\\n([\\s\\S]*?)" + fence, "g"))].map(match => match[1]);
  assert.equal(blocks.length, 2);
  const [emit, stub] = blocks;
  const expired = browser();
  runInNewContext(stub + "\n" + emit, expired.context);
  assert.equal(expired.context.Chatballs.eventQueue.length, 1);
  expired.advance(300001);
  assert.equal(expired.context.Chatballs.eventQueue.length, 0);

  const loaded = browser();
  runInNewContext(stub + "\n" + emit, loaded.context);
  const originalQueue = loaded.context.Chatballs.eventQueue;
  runInNewContext(loader, loaded.context);
  assert.equal(originalQueue.length, 0);
  assert.equal(loaded.messages.length, 0);
  loaded.context.handleSiteEventMessage({ type: "chatballs-site-events-ready",
    widgetKey: "PUBLIC_WIDGET_KEY", instanceId: "help-example" });
  assert.equal(loaded.messages.length, 1);
  assert.equal(loaded.messages[0].event.name, "checkout.help");
  assert.equal(loaded.messages[0].event.data.category, "coats");
}
process.stdout.write(JSON.stringify({ locales: articles.map(article => article.locale), examples: "passed", ttl: "passed" }));
