import { describe, expect, it } from "vitest";

import type { PortalThemeManifest } from "./types";
import {
  DEFAULT_PORTAL_THEME_ID,
  findPortalTheme,
  listPortalThemes,
  resolvePortalScheme,
  resolvePortalTheme,
  schemeOptions,
} from "./registry";

const manifests = import.meta.glob<{ manifest: PortalThemeManifest }>(
  "./*/manifest.ts",
  { eager: true },
);
const styles = import.meta.glob<string>("./*/theme.css", {
  eager: true,
  query: "?raw",
  import: "default",
});
const contract = import.meta.glob<string>("./contract.css", {
  eager: true,
  query: "?raw",
  import: "default",
})["./contract.css"];

const contractTokens = new Set(
  [...contract.matchAll(/(--help-[a-z0-9-]+)\s*:/g)].map((match) => match[1]),
);

function folderOf(path: string): string {
  return path.split("/")[1] ?? "";
}

/** Селекторы файла темы: @media/@supports разворачиваются, шаги @keyframes — нет. */
function selectorsOf(css: string): string[] {
  const cleaned = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const selectors: string[] = [];
  const stack: string[] = [];
  let buffer = "";
  for (const char of cleaned) {
    if (char === "{") {
      const head = buffer.trim();
      buffer = "";
      const insideKeyframes = stack.some((item) => item.startsWith("@keyframes"));
      const isWrapper = head.startsWith("@media") || head.startsWith("@supports");
      if (head && !insideKeyframes && !isWrapper) selectors.push(head);
      stack.push(head);
      continue;
    }
    if (char === "}") {
      stack.pop();
      buffer = "";
      continue;
    }
    buffer += char;
  }
  return selectors;
}

describe("каталог тем портала", () => {
  it("содержит тему по умолчанию", () => {
    expect(findPortalTheme(DEFAULT_PORTAL_THEME_ID)).not.toBeNull();
    expect(listPortalThemes()[0].id).toBe(DEFAULT_PORTAL_THEME_ID);
  });

  it("идентификатор темы совпадает с именем папки и уникален", () => {
    const ids = Object.entries(manifests).map(([path, module]) => {
      expect(module.manifest.id).toBe(folderOf(path));
      return module.manifest.id;
    });
    expect(new Set(ids).size).toBe(ids.length);
    expect(listPortalThemes()).toHaveLength(ids.length);
  });

  it("манифест заполнен и объявляет хотя бы одну схему", () => {
    for (const { manifest } of Object.values(manifests)) {
      expect(manifest.id).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
      expect(manifest.name.trim()).not.toBe("");
      expect(manifest.description.trim()).not.toBe("");
      expect(manifest.schemes.length).toBeGreaterThan(0);
      for (const scheme of manifest.schemes) {
        expect(["light", "dark"]).toContain(scheme);
      }
    }
  });

  it("каждая тема имеет файл стилей", () => {
    for (const path of Object.keys(manifests)) {
      expect(styles[`./${folderOf(path)}/theme.css`]).toBeTypeOf("string");
    }
  });

  it("правила темы скоупнуты её собственным атрибутом", () => {
    for (const [path, css] of Object.entries(styles)) {
      const id = folderOf(path);
      for (const selector of selectorsOf(css)) {
        if (selector.startsWith("@font-face")) continue;
        if (selector.startsWith("@keyframes")) {
          expect(selector.replace("@keyframes", "").trim()).toMatch(
            new RegExp(`^${id}-`),
          );
          continue;
        }
        expect(selector).toContain(`[data-portal-theme="${id}"]`);
      }
    }
  });

  it("тема объявляет только токены контракта", () => {
    for (const css of Object.values(styles)) {
      for (const match of css.matchAll(/(--[a-z0-9-]+)\s*:/g)) {
        expect(contractTokens).toContain(match[1]);
      }
    }
  });
});

describe("выбор темы и схемы", () => {
  const dual: PortalThemeManifest = {
    id: "dual",
    name: "Dual",
    description: "",
    schemes: ["light", "dark"],
    preview: { bg: "#fff", ink: "#000", accent: "#000" },
  };
  const lightOnly: PortalThemeManifest = { ...dual, id: "light-only", schemes: ["light"] };

  it("неизвестная тема деградирует до темы по умолчанию", () => {
    expect(resolvePortalTheme("no-such-theme").id).toBe(DEFAULT_PORTAL_THEME_ID);
  });

  it("SYSTEM следует системной схеме", () => {
    expect(resolvePortalScheme(dual, "SYSTEM", true)).toBe("dark");
    expect(resolvePortalScheme(dual, "SYSTEM", false)).toBe("light");
  });

  it("неподдерживаемая схема падает на основную схему темы", () => {
    expect(resolvePortalScheme(lightOnly, "DARK", false)).toBe("light");
    expect(resolvePortalScheme(lightOnly, "SYSTEM", true)).toBe("light");
  });

  it("в настройках предлагаются только поддерживаемые схемы", () => {
    expect(schemeOptions(lightOnly).map(([value]) => value)).toEqual(["LIGHT"]);
    expect(schemeOptions(dual).map(([value]) => value)).toEqual([
      "LIGHT",
      "DARK",
      "SYSTEM",
    ]);
  });
});
