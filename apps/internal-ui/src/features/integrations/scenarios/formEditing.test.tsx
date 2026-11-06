import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { AccessFields } from "./AccessFields";
import { ConstantValue } from "./ConstantValue";
import { exchangePairs, makePair } from "./exchangeModel";
import { pruneInputs } from "./inputParameters";
import { emptyDocument, schemaField } from "./model";
import { presentIssue } from "./issuePresentation";
import type { EditorCatalog } from "./types";

describe("service form editing", () => {
  it("removes unused generated inputs while preserving shared and authored inputs", () => {
    const document = emptyDocument();
    const unused = "input_00000000-0000-0000-0000-000000000001";
    const shared = "input_00000000-0000-0000-0000-000000000002";
    document.parameters.properties = { [unused]: { type: "string" }, [shared]: { type: "string" }, title: { type: "string" } };
    document.steps = [{ id: "step", kind: "action", inputs: { value: { source: "input", name: shared } } }];
    pruneInputs(document);
    expect(Object.keys(document.parameters.properties)).toEqual([shared, "title"]);
  });
  it("places nested errors at the actual field and supplies list removal", () => {
    const schema = schemaField("fields", { type: "object", properties: { phones: { type: "array", items: {
      type: "object", properties: { number: { type: "string", title: "Phone" } },
    } } } });
    const html = renderToStaticMarkup(<ConstantValue field={schema} value={{ phones: [{ number: "" }] }} connection=""
      issues={[{ path: "fields.phones.0.number", message: "Required phone" }]} onChange={() => undefined} />);
    expect(html).toContain("is-invalid");
    expect(html.match(/Required phone/g)).toHaveLength(1);
    expect(html).toContain('class="link is-muted"');
  });
  it("does not display empty access lists as all employees", () => {
    const document = emptyDocument();
    const catalog = { staff: [{ id: 1, name: "Employee" }], groups: [] } as unknown as EditorCatalog;
    const html = renderToStaticMarkup(<AccessFields value={document.access} catalog={catalog} onChange={() => undefined} />);
    expect(html).not.toContain('aria-checked="true"');
  });
  it("starts exchange in the direction supported by the actual descriptor", () => {
    const catalog = { entities: [{ key: "conversation", fields: schemaField("", { type: "object" }) }],
      adapters: [{ key: "bitrix24", entities: [{ key: "lead", nativeEntities: ["conversation"],
        synchronization: { directions: ["reverse"], deletion: ["unlink", "keep"] } }] }] } as unknown as EditorCatalog;
    expect(makePair(exchangePairs(catalog, "bitrix24")[0], 22).direction).toBe("reverse");
  });
  it("names the step and nested field in a validation error", () => {
    const document = emptyDocument();
    document.steps = [{ id: "create", kind: "action", name: "Create lead", connection: "chatballs", target: "chatballs:create" }];
    const catalog = { nativeActions: [{ key: "chatballs:create", input: schemaField("", { type: "object", properties: {
      fields: { type: "object", properties: { owner: { type: "string", title: "Owner" } } },
    } }) }] } as unknown as EditorCatalog;
    expect(presentIssue({ path: "steps.0.inputs.fields.owner.$", code: "null", message: "Required" }, document, catalog))
      .toEqual({ block: "create", message: "Create lead · Owner · Required" });
  });
});
