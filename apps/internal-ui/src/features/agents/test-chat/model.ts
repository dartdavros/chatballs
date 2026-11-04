import { formPayload, validField, type ClientField } from "@chatballs/shared";
import type { MessagePresentation } from "@chatballs/contracts";
import { fmt, t, tn } from "../../../i18n";
import type { Integration } from "../../integrations/model";
import type { ToolCall } from "../../../shared/tool-calls/model";
import type { ServiceField } from "../../integrations/services/types";

export type TestConnection = { id: number; name: string; fields: ClientField[] };
export type TestValues = Record<string, string | boolean>;
export type ClientData = {
  name?: string; email?: string; phone?: string;
  webFields?: Record<string, Record<string, string | number | boolean | null>>;
};
export type ChatMessage = { role: "user" | "assistant"; content: string };
export type TestAction = { state: string; runId?: string; title?: string; inputSchema?: ServiceField; arguments?: unknown };
export type TestTurn = MessagePresentation & { message: string; reply?: string; calls: ToolCall[]; error?: string; createdAt: string; serviceActions?: TestAction[] };
export type TestReply = MessagePresentation & { reply: string; toolCalls: ToolCall[]; serviceActions?: TestAction[] };

export function contactFields(): ClientField[] {
  return [
    { key: "name", label: t("pre_chat.name"), type: "string" },
    { key: "email", label: t("pre_chat.email"), type: "email" },
    { key: "phone", label: t("pre_chat.phone"), type: "phone" },
  ];
}

export function testConnections(items: Integration[], agentId: number): TestConnection[] {
  return items.filter((item) => item.provider === "WEB" && item.channel?.id === agentId).map((item) => ({
    id: item.id, name: item.name, fields: [...(item.config.fields ?? [])].sort((a, b) => a.order - b.order),
  }));
}

export const valueKey = (connectionId: number, fieldKey: string) => `${connectionId}:${fieldKey}`;

export function clientData(values: TestValues, connections: TestConnection[]): ClientData {
  const standard = Object.fromEntries(contactFields().flatMap((field) => {
    const value = values[field.key];
    return typeof value === "string" && value.trim() ? [[field.key, value.trim()]] : [];
  }));
  const webFields = Object.fromEntries(connections.flatMap((connection) => {
    const populated = connection.fields.filter((field) => {
      const value = values[valueKey(connection.id, field.key)];
      return typeof value === "boolean" || (typeof value === "string" && Boolean(value.trim()));
    });
    if (!populated.length) return [];
    const local = Object.fromEntries(populated.map((field) => [field.key, values[valueKey(connection.id, field.key)]]));
    return [[String(connection.id), formPayload(populated, local)]];
  }));
  return Object.keys(webFields).length ? { ...standard, webFields } : standard;
}

export function validClientData(values: TestValues, connections: TestConnection[]): boolean {
  return contactFields().every((field) => validField(field, values[field.key] ?? ""))
    && connections.every((connection) => connection.fields.every((field) =>
      validField(field, values[valueKey(connection.id, field.key)] ?? "")));
}

export function dataSummary(values: TestValues, connections: TestConnection[]): string {
  const fields = [...contactFields(), ...connections.flatMap((connection) => connection.fields.map((field) =>
    ({ ...field, key: valueKey(connection.id, field.key) })))];
  const filled = fields.filter((field) => {
    const value = values[field.key];
    return typeof value === "boolean" || (typeof value === "string" && Boolean(value.trim()));
  });
  const text = filled.filter((field) => field.type !== "boolean").slice(0, 2).map((field) => {
    const value = String(values[field.key]).trim();
    if (field.type === "enum") return field.options?.find((option) => option.value === value)?.label ?? "";
    if (field.type === "number" && Number.isFinite(Number(value))) return fmt.number(Number(value));
    if (field.type === "datetime") return fmt.shortDateTime(value);
    return value;
  });
  const remaining = filled.length - text.length;
  return [...text, remaining ? tn("agent_test.more_fields", remaining) : ""].filter(Boolean).join(" · ")
    || t("agent_test.data_summary");
}

export function displayReply(reply: string): string {
  return reply.replaceAll("<<HANDOFF>>", "").trim();
}

export function chatHistory(turns: TestTurn[]): ChatMessage[] {
  return turns.flatMap((turn) => turn.reply === undefined ? [] : [
    { role: "user" as const, content: turn.message }, { role: "assistant" as const, content: turn.reply },
  ]);
}
