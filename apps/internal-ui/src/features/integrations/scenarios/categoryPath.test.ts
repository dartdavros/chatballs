import { describe, expect, it } from "vitest";
import { parseCategoryPath, scenarioSnapshot, validCategoryPath } from "./categoryPath";
import { emptyDocument } from "./model";
import type { Scenario } from "./types";

const scenario: Scenario = { id: "one", name: "Scenario", revision: 1, enabled: false,
  definition: emptyDocument(), origin: { adapter: "", key: "", version: null }, connections: [], updatedAt: "" };

describe("scenario categories", () => {
  it("supports nested categories and clearing a category", () => {
    expect(parseCategoryPath(" Продажи / Лиды ")).toEqual(["Продажи", "Лиды"]);
    expect(parseCategoryPath("  ")).toEqual([]);
    expect(validCategoryPath([])).toBe(true);
    expect(validCategoryPath(parseCategoryPath("Продажи / Лиды"))).toBe(true);
  });

  it("keeps unfinished levels invalid instead of silently moving the scenario", () => {
    expect(validCategoryPath(parseCategoryPath("Продажи /"))).toBe(false);
    expect(validCategoryPath(parseCategoryPath("Продажи // Лиды"))).toBe(false);
    expect(validCategoryPath(["a", "b", "c", "d"])).toBe(false);
    expect(validCategoryPath(["x".repeat(81)])).toBe(false);
    expect(validCategoryPath(["a/b"])).toBe(false);
    expect(validCategoryPath(["a\nb"])).toBe(false);
    expect(validCategoryPath(["😀".repeat(80)])).toBe(true);
    expect(validCategoryPath(["😀".repeat(81)])).toBe(false);
  });

  it("includes category edits in the unsaved-changes snapshot", () => {
    expect(scenarioSnapshot(scenario)).toBe(scenarioSnapshot({ ...scenario, categoryPath: [] }));
    expect(scenarioSnapshot(scenario)).not.toBe(scenarioSnapshot({ ...scenario, categoryPath: ["Продажи"] }));
    expect(scenarioSnapshot({ ...scenario, categoryPath: ["Продажи"] }))
      .not.toBe(scenarioSnapshot({ ...scenario, categoryPath: ["Продажи", "Лиды"] }));
  });
});
