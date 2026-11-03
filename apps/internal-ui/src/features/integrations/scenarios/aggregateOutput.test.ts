import { describe, expect, it } from "vitest";
import { aggregateOutput } from "./aggregateOutput";
import { emptyDocument, schemaField } from "./model";
import { valueOptions } from "./bindingOptions";
import type { Block, EditorCatalog } from "./types";

describe("saved aggregate result bindings", () => {
  it("exposes branch results after join while keeping sibling values out of a branch", () => {
    const action = (id: string): Block => ({ id, kind: "action", connection: "chatballs", target: "chatballs:read" });
    const catalog = { context: schemaField("", { type: "object" }), scenarios: [], adapters: [], connections: [], events: [],
      nativeActions: [{ key: "chatballs:read", title: "Read", input: schemaField("", { type: "object" }),
        output: schemaField("", { type: "object", properties: { value: { type: "string" } } }) }] } as unknown as EditorCatalog;
    const parallel: Block = { id: "join", kind: "parallel", branches: [[action("left")], [action("right")]] };
    const document = emptyDocument(); document.steps = [parallel, action("after")];
    const branch = aggregateOutput(parallel, catalog)?.fields?.find(field => field.name === "branches")?.fields?.[0];
    expect(branch?.fields?.find(field => field.name === "steps")?.fields?.map(field => field.name)).toEqual(["left"]);
    expect(valueOptions(document, catalog, "after").some(option => option.binding.step === "join"
      && option.binding.path === "branches.0.steps.left.value")).toBe(true);
    expect(valueOptions(document, catalog, "right").some(option => option.binding.step === "left")).toBe(false);
  });
});
