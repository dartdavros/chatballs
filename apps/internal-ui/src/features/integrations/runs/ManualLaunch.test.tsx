import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { schemaField } from "../scenarios/model";
import { launchBody } from "./api";
import { ManualLaunch } from "./ManualLaunch";
import type { ManualAction } from "./types";

const action: ManualAction = {
  id: "1:contact.create", kind: "operation", title: "Create", connectionId: 1, operationKey: "contact.create",
  parameters: schemaField("", { type: "object", properties: { fields: { type: "object", properties: {
    NAME: { type: "string" },
    EMAIL: { type: "array", items: { type: "object", properties: { VALUE: { type: "string" } } } },
    PHONE: { type: "array", items: { type: "object", properties: { VALUE: { type: "string" } } } },
  } } } }),
  initialValues: { fields: { NAME: "Anna", EMAIL: [{ VALUE: "anna@example.test" }], PHONE: [{ VALUE: "+79991234567" }] } },
};

describe("manual form initial values", () => {
  it("renders known nested values on the first render, before preview or lookups", () => {
    const html = renderToStaticMarkup(<ManualLaunch action={action} conversationId={10}
      catalog={{ items: [action], files: [] }} onClose={() => {}} onRun={() => {}} />);
    for (const value of ["Anna", "anna@example.test", "+79991234567"]) expect(html).toContain(`value="${value}"`);
    expect(action.initialValues).toEqual({ fields: { NAME: "Anna", EMAIL: [{ VALUE: "anna@example.test" }], PHONE: [{ VALUE: "+79991234567" }] } });
  });

  it("sends exact edits, cleared arrays and the selected employee ID without reapplying defaults", () => {
    const parameters = { fields: { NAME: "", EMAIL: [], PHONE: [], ASSIGNED_BY_ID: "001" } };
    expect(launchBody(action, 10, parameters, "click")).toMatchObject({
      conversationId: 10, operationKey: "contact.create", parameters,
    });
    expect(launchBody(action, 11, {}, "other").parameters).toEqual({});
  });
});
