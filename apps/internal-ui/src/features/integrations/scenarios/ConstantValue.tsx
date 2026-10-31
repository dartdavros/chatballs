import { useState } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField, SwitchButton } from "../../../shared/form-controls";
import { fieldControl } from "../services/connect/fieldControls";
import type { ServiceField } from "../services/types";
import { LookupValue } from "./LookupValue";
import { AddObjectField } from "./AddObjectField";
import { inferredField, initialLiteral } from "./valueFields";
import type { EditorCatalog } from "./types";

export function ConstantValue({ field, value, connection, onChange, catalog }: {
  field: ServiceField; value: unknown; connection: string; onChange: (value: unknown) => void; catalog?: Pick<EditorCatalog, "files">;
}) {
  const [extraFields, setExtraFields] = useState<ServiceField[]>([]);
  if (field.control && !["lookup@1", "file@1"].includes(field.control)) {
    const Custom = fieldControl(field);
    return Custom ? <Custom field={field} value={value} disabled={false} onChange={onChange} />
      : <FormField label={field.title} value="" disabled error={t("scenarios.control_unavailable")} wide />;
  }
  if (field.type === "file") return <SelectField label={field.title} value={value && typeof value === "object" && "fileId" in value ? String(value.fileId) : ""}
    options={[["", t("scenarios.select")], ...(catalog?.files ?? []).map(file => [file.id, file.name] as [string, string])]}
    onChange={fileId => onChange({ fileId })} wide />;
  if (field.type === "object") {
    const object: Record<string, unknown> = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
    const known = [...(field.fields ?? []), ...extraFields];
    const fields = [...known, ...Object.keys(object).filter(name => !known.some(f => f.name === name)).map(name => inferredField(name, object[name]))];
    return <div className="scenario-bound-children">{fields.map(child => <ConstantValue key={child.name} field={child} value={object[child.name]} catalog={catalog}
      connection={connection} onChange={next => onChange({ ...object, [child.name]: next })} />)}
      {field.open && <AddObjectField names={fields.map(f => f.name)} onAdd={child => { setExtraFields([...extraFields, child]); onChange({ ...object, [child.name]: initialLiteral(child) }); }} />}
    </div>;
  }
  if (field.type === "array" && field.items) {
    const items = Array.isArray(value) ? value : [];
    return <div className="scenario-bound-children">{items.map((item, index) => <ConstantValue key={index} field={field.items!} value={item} catalog={catalog}
      connection={connection} onChange={next => onChange(items.map((v, i) => i === index ? next : v))} />)}
      <button type="button" className="link" onClick={() => onChange([...items, initialLiteral(field.items!)])}>{t("scenarios.add_item")}</button></div>;
  }
  if (field.type === "lookup") return <LookupValue field={field} value={value} connection={connection} onChange={onChange} />;
  if (field.type === "enum") return <SelectField label={field.title} value={String(field.options?.findIndex(option => option.value === value) ?? -1)}
    options={[["-1", t("scenarios.select")], ...(field.options ?? []).map((option, index) => [String(index), option.label] as [string, string])]}
    onChange={index => onChange(field.options?.[Number(index)]?.value)} wide />;
  const Control = fieldControl({ ...field, control: field.control.startsWith("lookup@") ? "" : field.control });
  if (Control) return <><Control field={field} value={value} disabled={false} onChange={onChange} />
    {field.nullable && <div className="scenario-toggle"><span>{t("scenarios.nullable")}</span><SwitchButton className="ui-switch is-compact"
      label={t("scenarios.nullable")} checked={value === null} onClick={() => onChange(value === null ? "" : null)} /></div>}</>;
  return <FormField label={field.title} value="" disabled error={t("scenarios.control_unavailable")} wide />;
}
