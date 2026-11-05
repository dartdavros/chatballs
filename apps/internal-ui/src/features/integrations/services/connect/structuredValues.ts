import type { ServiceField } from "../types";

export type ValueKind = "string" | "number" | "boolean" | "object" | "array" | "null";
export function valueKind(value: unknown): ValueKind {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "object") return "object";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  return "string";
}
export function emptyValue(kind: string): unknown {
  return kind === "null" ? null : kind === "object" ? {} : kind === "array" ? []
    : kind === "boolean" ? false : kind === "number" ? 0 : "";
}
export function jsonField(name: string, title = name): ServiceField {
  return { name, title, type: "json", nullable: true, required: false, secret: false,
    control: "structured_value@1", hint: "", placeholder: "" };
}
export function replaceEntry(object: Record<string, unknown>, index: number, name: string, value: unknown) {
  return Object.fromEntries(Object.entries(object).map((entry, i) => i === index ? [name, value] : entry));
}

