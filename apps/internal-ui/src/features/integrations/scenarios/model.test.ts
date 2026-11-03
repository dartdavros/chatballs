import { describe, expect, it } from "vitest";
import { blockPath, copyBlock, emptyDocument, listAt, newBlock, schemaField } from "./model";
import { valueOptions } from "./bindingOptions";
import { sameReference } from "./referenceModel";
import { conditionOptions, newCondition } from "./conditionModel";
import type { Block, EditorCatalog } from "./types";

describe("scenario document editing", () => {
  it("copies composite IDs and internal references without rewriting literal data or external references", () => {
    const original: Block = { id: "loop", kind: "foreach", list: { source: "step", step: "search", path: "rows" }, body: [
      { id: "action", kind: "action", inputs: { item: { source: "item", step: "loop", path: "id" },
        literal: { source: "constant", value: { id: "loop", step: "action" } } } },
    ] };
    const copied = copyBlock(original);
    expect(copied.id).not.toBe(original.id);
    expect(copied.body![0].id).not.toBe("action");
    expect(copied.body![0].inputs!.item).toEqual({ source: "item", step: copied.id, path: "id" });
    expect(copied.body![0].inputs!.literal).toEqual(original.body![0].inputs!.literal);
    expect(copied.list).toEqual(original.list);
    expect(original.body![0].id).toBe("action");
    expect(blockPath([copied], copied.body![0].id)).toBe("steps.0.body.0");
    expect(listAt([copied], { parent: copied.id, branch: "body" })).toBe(copied.body);
  });

  it("offers iteration fields for parameter lists only inside the loop", () => {
    const document = emptyDocument();
    document.parameters.properties = { rows: { type: "array", items: { type: "object", properties: { name: { type: "string" } } } } };
    document.steps = [{ id: "loop", kind: "foreach", list: { source: "parameter", name: "rows" }, body: [{ id: "inside", kind: "action" }] }, { id: "outside", kind: "action" }];
    const catalog = { context: schemaField("", { type: "object" }), scenarios: [], adapters: [], connections: [], events: [], nativeActions: [] } as unknown as EditorCatalog;
    const inside = valueOptions(document, catalog, "inside");
    expect(inside.some(o => o.binding.source === "item" && o.binding.path === "name")).toBe(true);
    expect(valueOptions(document, catalog, "outside").some(o => o.binding.source === "item")).toBe(false);
    expect(newBlock("parallel").branches).toHaveLength(2);
  });

  it("offers typed step outcomes after all block kinds without leaking sibling branches", () => {
    const document = emptyDocument();
    document.steps = [{ id: "parallel", kind: "parallel", branches: [[{ id: "first", kind: "wait" }], [{ id: "sibling", kind: "wait" }]] },
      { id: "after", kind: "wait" }];
    const catalog = { context: schemaField("", { type: "object" }), scenarios: [], adapters: [], connections: [], events: [], nativeActions: [] } as unknown as EditorCatalog;
    const options = conditionOptions(document, catalog, "after");
    const states = options.filter(option => option.binding.aspect === "state");
    expect(states.map(o => o.binding)).toEqual([{ source: "step", step: "parallel", aspect: "state" }]);
    expect(options.every(option => option.binding.step === "parallel")).toBe(true);
    expect(options.some(option => option.binding.path === "branches.0.state")).toBe(true);
    expect(newCondition("step", states).right?.value).toBe("completed");
    expect(valueOptions(document, catalog, "sibling").some(o => o.binding.step === "first")).toBe(false);
    expect(sameReference({ step: "parallel", aspect: "state", source: "step" }, states[0].binding)).toBe(true);
    expect(sameReference({ source: "step", step: "parallel", path: "" }, states[0].binding)).toBe(false);
  });
});
