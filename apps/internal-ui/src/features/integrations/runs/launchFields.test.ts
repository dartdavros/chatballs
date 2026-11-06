import { describe, expect, it } from "vitest";
import { requiredIssues } from "./launchFields";
import { schemaField } from "../scenarios/model";

describe("manual launch validation", () => {
  const schema = schemaField("", { type: "object", properties: {
    fields: { type: "object", required: true, properties: {
      title: { type: "string", required: true },
      phones: { type: "array", items: { type: "object", properties: { value: { type: "string", required: true } } } },
    } },
    options: { type: "object", properties: { unused: { type: "string", required: true } } },
  } });
  it("validates actual required values without opening an optional object", () => {
    expect(requiredIssues(schema, {}).map(issue => issue.path)).toEqual(["fields"]);
    expect(requiredIssues(schema, { fields: { title: "Lead" } })).toEqual([]);
    expect(requiredIssues(schema, { fields: { title: " ", phones: [{ value: "" }] } }).map(issue => issue.path))
      .toEqual(["fields.title", "fields.phones.0.value"]);
  });
  it("accepts zero, false and an explicitly nullable value", () => {
    for (const value of [0, false, null]) expect(requiredIssues(schemaField("value", { type: "json", required: true, nullable: true }), value)).toEqual([]);
  });
});
