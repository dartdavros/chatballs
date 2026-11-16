import { describe, expect, it } from "vitest";
import { testData, testFields, validValues, type TestDefinition } from "./test-model";

describe("external test scope input", () => {
  const definition: TestDefinition = { standardFields: ["name"], customFields: [
    { sourceConnectionId: 1, fieldId: "field-a", sourceName: "First", label: "City", type: "number" },
    { sourceConnectionId: 2, fieldId: "field-a", sourceName: "Second", label: "City", type: "boolean" },
  ] };
  it("uses only explicitly permitted source/field identities and retains zero and false", () => {
    expect(testData(definition, { name: " Test ", email: "ignored@example.invalid", "1:field-a": "0", "2:field-a": false, "1:city": "ignored" })).toEqual({
      standardFields: { name: "Test" }, customFields: [
        { sourceConnectionId: 1, fieldId: "field-a", value: 0 }, { sourceConnectionId: 2, fieldId: "field-a", value: false },
      ],
    });
    expect(testFields({ standardFields: [], customFields: [] })).toEqual([]);
    expect(testData(definition, {})).toEqual({ standardFields: {}, customFields: [] });
  });
  it("validates against the current permitted type", () => {
    expect(validValues(definition, { "1:field-a": "not a number" })).toBe(false);
    expect(validValues(definition, { "1:field-a": "0" })).toBe(true);
  });
});
