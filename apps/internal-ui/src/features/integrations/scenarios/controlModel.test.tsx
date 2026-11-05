import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { registerFieldControl, type ControlProps } from "../services/connect/fieldControls";
import { displayRunValue } from "../runs/RunValues";
import { ConstantValue } from "./ConstantValue";
import { unavailableField, unavailableScenarioControl } from "./controlModel";
import { emptyDocument, schemaField } from "./model";
import type { EditorCatalog } from "./types";

describe("scenario schema controls", () => {
  it("uses vocabulary labels and a safe fallback without changing machine values", () => {
    const field = { ...schemaField("failure", { type: "string" }),
      options: [{ value: "PROVIDER_FAILURE", label: "Provider unavailable" }], placeholder: "Operation could not finish" };
    expect(displayRunValue(field, "PROVIDER_FAILURE")).toBe("Provider unavailable");
    expect(displayRunValue(field, "FUTURE_INTERNAL_DIAGNOSTIC")).toBe("Operation could not finish");
    const numeric = { ...schemaField("score", { type: "enum" }), options: [{ value: 1, label: "Needs attention" }] };
    expect(displayRunValue(numeric, 1)).toBe("Needs attention");
  });

  it("shows a file name without exposing its operational identifier", () => {
    const field = schemaField("report", { type: "file", title: "Report" });
    expect(displayRunValue(field, { fileId: "private-operational-id" }, { "private-operational-id": "support-report.csv" })).toBe("support-report.csv");
    expect(displayRunValue(field, { fileId: "private-operational-id" })).not.toContain("private-operational-id");
    expect(displayRunValue({ ...field, secret: true }, { redacted: true })).not.toContain("support-report.csv");
  });

  it("names compound parameters and their items in the shared launch form", () => {
    const field = schemaField("recipients", { type: "array", title: "Recipients",
      items: { type: "object", properties: { name: { type: "string", title: "Name" } } } });
    const rendered = renderToStaticMarkup(<ConstantValue field={field} value={[{ name: "Operator" }]}
      connection="chatballs" onChange={() => undefined} />);
    expect(rendered).toContain('role="group" aria-label="Recipients"');
    expect(rendered).toContain("Operator");
    expect(rendered).toContain("Name");
  });

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
