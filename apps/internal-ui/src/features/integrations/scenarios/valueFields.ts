import type { ServiceField } from "../services/types";
import type { SchemaNode } from "../../skills/template-editor/schema";
import type { BoundValue } from "./types";

export function inferredField(name: string, value: unknown): ServiceField {
  const type = value === null ? "json" : Array.isArray(value) ? "array" : value && typeof value === "object" ? "object"
    : typeof value === "number" ? "number" : typeof value === "boolean" ? "boolean" : "string";
  return { name, title: name, type, required: false, nullable: value === null, open: true, hint: "", placeholder: "", secret: false, control: "",
    ...(type === "array" ? { items: { ...inferredField("", ""), type: "json", nullable: true, control: "structured_value@1" } } : {}),
    ...(type === "object" ? { fields: Object.entries(value as object).map(([key, child]) => inferredField(key, child)) } : {}) };
}
export function fieldFromNode(name: string, node: SchemaNode): ServiceField {
  return { ...inferredField(name, ""), type: node.type === "list" ? "array" : node.type, required: node.required ?? false,
    fields: node.properties ? Object.entries(node.properties).map(([key, child]) => fieldFromNode(key, child)) : undefined,
    items: node.items ? fieldFromNode("", node.items) : undefined, open: node.type === "object" };
}
export function initialLiteral(field: ServiceField): unknown {
  return field.type === "object" ? {} : field.type === "array" ? [] : field.type === "boolean" ? false : ["number", "integer"].includes(field.type) ? 0 : "";
}
export function initialBound(field: ServiceField): BoundValue {
  return field.type === "object" ? {} : field.type === "array" ? [] : { source: "constant", value: initialLiteral(field) };
}
