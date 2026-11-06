import { t } from "../../../i18n";
import type { ServiceField } from "../services/types";
import type { ValueIssue } from "../scenarios/ConstantValue";

export function requiredIssues(field: ServiceField, value: unknown, path = ""): ValueIssue[] {
  const empty = value === undefined || value === null && !field.nullable || typeof value === "string" && !value.trim();
  if (empty) return field.required ? [{ path, message: t("services.field_required") }] : [];
  if (field.type === "object" && value && typeof value === "object" && !Array.isArray(value)) {
    return (field.fields ?? []).flatMap(child => requiredIssues(child, (value as Record<string, unknown>)[child.name], path ? `${path}.${child.name}` : child.name));
  }
  if (field.type === "array" && field.items && Array.isArray(value)) {
    return value.flatMap((item, index) => requiredIssues(field.items!, item, `${path}.${index}`));
  }
  return [];
}
