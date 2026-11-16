import type { ClientField } from "@chatballs/shared";
import { validField, formPayload } from "@chatballs/shared";
import type { MessagePresentation } from "@chatballs/contracts";
import type { SettingsCatalog } from "../../settings/external-agent/model";
import { contactFields, type TestValues } from "../test-chat/model";

export type TestDefinition = { standardFields: string[]; customFields: SettingsCatalog["customFields"] };
export type ExternalTestState = "idle" | "waiting" | "longWaiting" | "ready" | "blocked" | "error" | "handoff" | "unknown" | "partial";
export type ExternalTestMessage = MessagePresentation & {
  id: number; role: "user" | "assistant"; text: string; createdAt: string; kind: string; filename: string; fileUrl: string | null;
};
export type ExternalTestSession = { id: string; available: boolean; state: ExternalTestState; messages: ExternalTestMessage[] };
export const fieldKey = (source: number, id: string) => `${source}:${id}`;
export function testFields(definition: TestDefinition): ClientField[] {
  return [...contactFields().filter(field => definition.standardFields.includes(field.key)),
    ...definition.customFields.map(field => ({ key: fieldKey(field.sourceConnectionId, field.fieldId), label: field.label,
      type: field.type as ClientField["type"], options: field.options }))];
}
export const validValues = (definition: TestDefinition, values: TestValues) => testFields(definition).every(field => validField(field, values[field.key] ?? ""));
export function testData(definition: TestDefinition, values: TestValues) {
  const populated = testFields(definition).filter(field => typeof values[field.key] === "boolean" || String(values[field.key] ?? "").trim());
  const data = formPayload(populated, values);
  return { standardFields: Object.fromEntries(definition.standardFields.filter(key => key in data).map(key => [key, data[key]])),
    customFields: definition.customFields.filter(field => fieldKey(field.sourceConnectionId, field.fieldId) in data).map(field => ({
      sourceConnectionId: field.sourceConnectionId, fieldId: field.fieldId, value: data[fieldKey(field.sourceConnectionId, field.fieldId)],
    })) };
}
