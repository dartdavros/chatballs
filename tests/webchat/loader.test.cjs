const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const assets = join(__dirname, "../../apps/backend/chatballs/webchat/loader_assets");
function loaderSource() {
  let source = readFileSync(join(assets, "runtime.js"), "utf8");
  for (const module of ["site_fields", "observations", "appearance", "launcher", "site_events", "site_invitation", "genie"]) {
    source = source.replace(`/*__${module.toUpperCase()}__*/`, () => readFileSync(join(assets, `${module}.js`), "utf8"));
  }
  return source;
}

function context() {
  const ctx = vm.createContext({ URL, origin: "https://widget.example" });
  vm.runInContext(readFileSync(join(assets, "appearance.js"), "utf8"), ctx);
  vm.runInContext(readFileSync(join(assets, "genie.js"), "utf8"), ctx);
  return ctx;
}

test("launcher configuration covers both sides, all sizes and all shapes", () => {
  const ctx = context();
  for (const position of ["left", "right"]) {
    for (const size of [48, 56, 64]) {
      for (const shape of ["circle", "rounded", "square"]) {
        ctx.appearance = ctx.readAppearance({ available: true, appearance: {
          accent: "#0d8a7e", launcherPosition: position, launcherSize: size, launcherShape: shape,
          launcherIcon: "/api/v1/webchat/assets/icon/",
        } });
        assert.equal(ctx.appearance.position, position);
        assert.equal(ctx.appearance.size, size);
        assert.equal(ctx.appearance.shape, shape);
        assert.deepEqual(Array.from(ctx.appearance.rgb), [13, 138, 126]);
        assert.equal(ctx.appearance.icon, "https://widget.example/api/v1/webchat/assets/icon/");
        assert.equal(ctx.launcherRadius(), shape === "square" ? 10 : size * (shape === "rounded" ? .3 : .5));
      }
    }
  }
});

test("legacy accent works and absent configuration leaves the default launcher", () => {
  const ctx = context();
  const legacy = ctx.readAppearance({ available: true, accent: "#BE123C" });
  assert.deepEqual(Array.from(legacy.rgb), [190, 18, 60]);
  assert.equal(legacy.position, "right");
  assert.equal(legacy.size, 56);
  assert.equal(legacy.shape, "circle");
  for (const response of [null, {}, { available: false }, { available: false, appearance: {} }]) {
    assert.equal(ctx.readAppearance(response), null);
  }
  assert.equal(ctx.appearance.accent, "#1677ff");
});

test("invalid configuration is rejected before any appearance is applied", () => {
  const ctx = context();
  for (const appearance of [null, [], "text", { accent: "red" }, { launcherSize: 50 },
    { launcherSize: true }, { launcherPosition: "top" }, { launcherShape: "oval" },
    { launcherIcon: 42 }, { launcherIcon: "javascript:alert(1)" },
    { launcherIcon: "//evil.example/icon.svg" }, { launcherIcon: "data:image/svg+xml,<svg/>" },
    { launcherIcon: '/icon.svg" onerror="alert(1)' }]) {
    assert.throws(() => ctx.readAppearance({ available: true, appearance }));
    assert.equal(ctx.appearance.accent, "#1677ff");
  }
});

test("genie geometry mirrors across the viewport and ends in the selected launcher shape", () => {
  const ctx = context();
  const viewport = 1280;
  const panel = { top: 100, bottom: 708, cx: 1036, half: 220, radius: 24 };
  for (const size of [48, 56, 64]) {
    for (const radius of [size / 2, size * .3, 10]) {
      const icon = { top: 720, bottom: 720 + size, cx: 1224, half: size / 2, radius };
      for (const p of [0, .25, .5, .75, 1]) {
        const right = ctx.shapeAt(p, panel, icon);
        const left = ctx.shapeAt(p, { ...panel, cx: viewport - panel.cx }, { ...icon, cx: viewport - icon.cx });
        assert.ok(Math.abs(left.topL - (viewport - right.topRt)) < 1e-9);
        assert.ok(Math.abs(left.bottomRt - (viewport - right.bottomL)) < 1e-9);
        assert.equal(left.topY, right.topY);
        assert.equal(left.bottomY, right.bottomY);
        assert.ok(!/NaN|Infinity/.test(ctx.pathOf(left, 0, 0)));
        if (p === 1) {
          assert.equal(left.topR, radius);
          assert.equal(left.bottomR, radius);
        }
      }
    }
  }
});

test("all loader modules assemble into one valid standalone script", () => {
  assert.doesNotThrow(() => new vm.Script(loaderSource()));
});

test("public loader delegates only microphone to the iframe src before mounting", () => {
  let insertedFrames = 0;
  let mountedFrames = 0;
  function element(tagName) {
    return {
      tagName, children: [], dataset: {}, style: { setProperty() {}, removeProperty() {} },
      setAttribute(name, value) { this[name] = value; },
      addEventListener() {},
      appendChild(child) {
        if (child.tagName === "iframe") {
          assert.equal(new URL(child.src).origin, "https://widget.example:8443");
          assert.equal(child.allow, "microphone 'src'");
          insertedFrames += 1;
        }
        this.children.push(child);
        return child;
      },
    };
  }
  const body = element("body");
  const appendToBody = body.appendChild;
  body.appendChild = function (child) {
    for (const frame of child.children.filter((node) => node.tagName === "iframe")) {
      assert.equal(frame.allow, "microphone 'src'");
      mountedFrames += 1;
    }
    return appendToBody.call(this, child);
  };
  vm.runInNewContext(loaderSource(), {
    URL,
    location: { href: "https://host.example/page", origin: "https://host.example" },
    document: {
      addEventListener() {},
      currentScript: {
        src: "https://widget.example:8443/chat-widget.js",
        getAttribute: (name) => name === "data-widget-key" ? "public-key" : null,
      },
      head: element("head"), body, createElement: element,
    },
    window: {
      addEventListener() {},
      clearTimeout() {},
      setTimeout() {},
      matchMedia: () => ({ matches: false, addEventListener() {} }),
    },
    Audio: function () {},
  });
  assert.equal(insertedFrames, 1);
  assert.equal(mountedFrames, 1);
});
