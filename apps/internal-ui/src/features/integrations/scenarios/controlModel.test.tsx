import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { registerFieldControl, type ControlProps } from "../services/connect/fieldControls";
import { ConstantValue } from "./ConstantValue";
import { unavailableField, unavailableScenarioControl } from "./controlModel";
import { emptyDocument, schemaField } from "./model";
import type { EditorCatalog } from "./types";

describe("scenario schema controls", () => {
  it("uses a registered compound control and refuses a missing version", () => {
    const field = { ...schemaField("data", { type: "object" }), control: "scenario.compound@1" };
    expect(unavailableField(field)).toBe(true);
    registerFieldControl(field.control, ({ field, value }: ControlProps) => <input aria-label={field.title} readOnly value={JSON.stringify(value)} />);
    expect(unavailableField(field)).toBe(false);
    const rendered = renderToStaticMarkup(<ConstantValue field={field} value={{ result: 42 }} connection="" onChange={() => undefined} />);
    expect(rendered).toContain("42");
    expect(unavailableField({ ...field, control: "scenario.compound@2" })).toBe(true);
  });

  it("blocks selected nested operation schemas with unavailable controls without blocking unrelated actions", () => {
    const input = schemaField("", { type: "object", properties: { field: { type: "string" } } });
    input.fields![0].control = "not_installed@1";
    const catalog = { nativeActions: [{ key: "chatballs:example", input }], transforms: [] } as unknown as EditorCatalog;
    const document = emptyDocument();
    document.steps = [{ id: "if", kind: "if", then: [{ id: "a", kind: "action", connection: "chatballs", target: "chatballs:example" }], else: [] }];
    expect(unavailableScenarioControl(document, catalog)).toBe(true);
    document.steps = [];
    expect(unavailableScenarioControl(document, catalog)).toBe(false);
  });
});
