import { renderToStaticMarkup } from "react-dom/server";
import { isValidElement, type FunctionComponent } from "react";
import { describe, expect, it } from "vitest";

import type { ServiceField } from "../types";
import { SchemaFields } from "./SchemaFields";
import { fieldControl, registerFieldControl, unsupportedFields, type ControlProps } from "./fieldControls";

const field = (changes: Partial<ServiceField>): ServiceField => ({
  name: "value", type: "string", title: "Value", hint: "", placeholder: "", required: true,
  nullable: false, secret: false, control: "", ...changes,
});

describe("service form schema contract", () => {
  it("keeps a webhook URL visible during entry and masks a password", () => {
    const fields = [field({ name: "url", control: "url@1", secret: true }), field({ name: "password", control: "secret@1", secret: true })];
    const html = renderToStaticMarkup(<SchemaFields fields={fields} values={{}} errors={{}} disabled={false} onChange={() => {}} />);
    expect(html).toContain('type="text"');
    expect(html).toContain('type="password"');
  });

  it("renders typed numbers and booleans using shared controls", () => {
    const html = renderToStaticMarkup(<SchemaFields fields={[field({ name: "count", type: "integer" }), field({ name: "enabled", type: "boolean" })]}
      values={{ count: 12, enabled: true }} errors={{}} disabled={false} onChange={() => {}} />);
    expect(html).toContain('type="number"');
    expect(html).toContain('value="12"');
    expect(html).toContain('aria-checked="true"');
  });

  it("requires the exact installed control version and never substitutes a text field", () => {
    const custom = field({ control: "installed.lookup@2" });
    expect(unsupportedFields([custom])).toBe(true);
    expect(fieldControl(custom)).toBeUndefined();
    registerFieldControl("installed.lookup@2", () => null);
    expect(unsupportedFields([custom])).toBe(false);
    expect(unsupportedFields([{ ...custom, control: "installed.lookup@3" }])).toBe(true);
    expect(() => registerFieldControl("installed.lookup@2", () => null)).toThrow();
  });

  it("sends numbers as numbers without turning an empty field into zero", () => {
    const number = field({ type: "number", control: "number@1" });
    const Control = fieldControl(number) as FunctionComponent<ControlProps>;
    const values: unknown[] = [];
    const input = Control({ field: number, value: "", disabled: false, onChange: (value) => values.push(value) });
    if (!isValidElement<{ onChange: (value: string) => void }>(input)) throw new Error("Expected shared input");
    input.props.onChange("12.5");
    input.props.onChange("");
    expect(values).toEqual([12.5, ""]);
  });

  it("preserves the JSON type of a selected numeric enum", () => {
    const enumField = field({ type: "enum", options: [{ value: 2, label: "Two" }, { value: "2", label: "Text" }] });
    const Control = fieldControl(enumField) as FunctionComponent<ControlProps>;
    const values: unknown[] = [];
    const select = Control({ field: enumField, value: 2, disabled: false, onChange: (value) => values.push(value) });
    if (!isValidElement<{ onChange: (value: string) => void }>(select)) throw new Error("Expected shared select");
    select.props.onChange("0");
    select.props.onChange("1");
    expect(values).toEqual([2, "2"]);
  });
});
