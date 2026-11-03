import { Fragment } from "react";
import { fmt, t } from "../../../i18n";
import type { ServiceField } from "../services/types";

function entries(field: ServiceField, value: unknown, label = field.title): Array<[string, string]> {
  if (value && typeof value === "object" && "redacted" in value) return [[label, t("runs.hidden")]];
  if (field.type === "object" && value && typeof value === "object" && !Array.isArray(value)) {
    return (field.fields ?? []).flatMap(child => entries(child, (value as Record<string, unknown>)[child.name],
      label ? `${label} · ${child.title}` : child.title));
  }
  if (Array.isArray(value) && field.items) return value.flatMap((child, index) => entries(field.items!, child, `${label} · ${fmt.number(index + 1)}`));
  if (value === undefined) return [];
  const text = value === null ? "—" : typeof value === "number" ? fmt.number(value)
    : typeof value === "boolean" ? t(value ? "scenarios.yes" : "scenarios.no")
    : field.type === "datetime" && typeof value === "string" ? fmt.shortDateTime(value)
    : field.type === "enum" ? field.options?.find(option => option.value === value)?.label ?? String(value)
    : typeof value === "string" ? value : "—";
  return [[label, text]];
}

export function RunValues({ schema, value }: { schema: ServiceField | null; value: unknown }) {
  const rows = schema ? entries(schema, value, schema.type === "object" ? "" : schema.title) : [];
  if (!rows.length) return null;
  return <dl className="run-values">{rows.map(([label, text], i) => <Fragment key={`${label}:${i}`}><dt>{label}</dt><dd>{text}</dd></Fragment>)}</dl>;
}

export function displayRunValue(schema: ServiceField | null, value: unknown): string {
  if (schema) return entries(schema, value, "").map(([label, text]) => label ? `${label}: ${text}` : text).join(" · ") || "—";
  return typeof value === "number" ? fmt.number(value) : typeof value === "string" ? value : "—";
}
