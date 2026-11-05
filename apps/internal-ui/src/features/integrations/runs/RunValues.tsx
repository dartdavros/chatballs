import { Fragment } from "react";
import { fmt, t } from "../../../i18n";
import type { ServiceField } from "../services/types";
import { jsonField } from "../services/connect/structuredValues";

function entries(field: ServiceField, value: unknown, label = field.title, fileNames: Record<string, string> = {}): Array<[string, string]> {
  if (value && typeof value === "object" && "redacted" in value) return [[label, t("runs.hidden")]];
  if (["object", "json"].includes(field.type) && value && typeof value === "object" && !Array.isArray(value)) {
    const known = field.fields ?? [];
    const fields = [...known, ...(field.open || field.type === "json" ? Object.keys(value)
      .filter(name => !known.some(child => child.name === name)).map(name => jsonField(name)) : [])];
    return fields.flatMap(child => entries(child, (value as Record<string, unknown>)[child.name],
      label ? `${label} · ${child.title}` : child.title, fileNames));
  }
  if (Array.isArray(value) && (field.items || field.type === "json")) return value.flatMap((child, index) =>
    entries(field.items ?? jsonField(""), child, `${label} · ${fmt.number(index + 1)}`, fileNames));
  if (value === undefined) return [];
  if (field.type === "file" && value && typeof value === "object") {
    const name = "fileId" in value && typeof value.fileId === "string" ? fileNames[value.fileId] : undefined;
    return [[label, name || t("scenarios.type_file")]];
  }
  const text = value === null ? "—"
    : field.options?.length ? field.options.find(option => option.value === value)?.label ?? (field.placeholder || String(value))
    : typeof value === "number" ? fmt.number(value)
    : typeof value === "boolean" ? t(value ? "scenarios.yes" : "scenarios.no")
    : field.type === "datetime" && typeof value === "string" ? fmt.shortDateTime(value)
    : typeof value === "string" ? value : "—";
  return [[label, text]];
}

export function RunValues({ schema, value, fileNames }: { schema: ServiceField | null; value: unknown; fileNames?: Record<string, string> }) {
  const rows = schema ? entries(schema, value, schema.type === "object" ? "" : schema.title, fileNames) : [];
  if (!rows.length) return null;
  return <dl className="run-values">{rows.map(([label, text], i) => <Fragment key={`${label}:${i}`}><dt>{label}</dt><dd>{text}</dd></Fragment>)}</dl>;
}

export function displayRunValue(schema: ServiceField | null, value: unknown, fileNames?: Record<string, string>): string {
  if (schema) return entries(schema, value, "", fileNames).map(([label, text]) => label ? `${label}: ${text}` : text).join(" · ") || "—";
  return typeof value === "number" ? fmt.number(value) : typeof value === "string" ? value : "—";
}
