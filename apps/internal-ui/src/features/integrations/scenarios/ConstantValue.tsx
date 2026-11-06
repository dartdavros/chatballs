import { useState, type ReactNode } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField, SwitchButton } from "../../../shared/form-controls";
import { fieldControl } from "../services/connect/fieldControls";
import type { ServiceField } from "../services/types";
import { LookupValue } from "./LookupValue";
import { AddObjectField } from "./AddObjectField";
import { inferredField, initialLiteral } from "./valueFields";
import type { EditorCatalog } from "./types";

export type ValueIssue = { path: string; message: string };
function FieldError({ error }: { error?: string }) {
  return error ? <small className="form-field-error" role="alert">{error}</small> : null;
}
function CompoundValue({ title, children, error }: { title: string; children: ReactNode; error?: string }) {
  const fields = <div className="scenario-bound-children">{children}</div>;
  return title ? <div className="readonly-field wide" role="group" aria-label={title}>
    <span>{title}</span>{fields}<FieldError error={error} /></div> : fields;
}

export function ConstantValue({ field, value, connection, onChange, catalog, issues = [], path = field.name }: {
  field: ServiceField; value: unknown; connection: string; onChange: (value: unknown) => void; catalog?: Pick<EditorCatalog, "files">;
  issues?: ValueIssue[]; path?: string;
}) {
  const [extraFields, setExtraFields] = useState<ServiceField[]>([]);
  const error = issues.find(issue => issue.path.replace(/\.\$$/, "") === path)?.message;
  if (field.control && !["lookup@1", "file@1"].includes(field.control)) {
    const Custom = fieldControl(field);
    return Custom ? <><Custom field={field} value={value} disabled={false} error={error} onChange={onChange} />
      {["select@1", "textarea@1"].includes(field.control) && <FieldError error={error} />}</>
      : <FormField label={field.title} value="" disabled error={t("scenarios.control_unavailable")} wide />;
  }
  if (field.type === "file") return <><SelectField label={field.title} invalid={Boolean(error)} value={value && typeof value === "object" && "fileId" in value ? String(value.fileId) : ""}
    options={[["", t("scenarios.select")], ...(catalog?.files ?? []).map(file => [file.id, file.name] as [string, string])]}
    onChange={fileId => onChange(fileId ? { fileId } : undefined)} wide /><FieldError error={error} /></>;
  if (field.type === "object") {
    const object: Record<string, unknown> = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
    const known = [...(field.fields ?? []), ...extraFields];
    const fields = [...known, ...Object.keys(object).filter(name => !known.some(f => f.name === name)).map(name => inferredField(name, object[name]))];
    return <CompoundValue title={field.title} error={error}>{fields.map(child => <div className="scenario-bound-field" key={child.name}>
      <ConstantValue field={{ ...child, secret: field.secret || child.secret }} value={object[child.name]} catalog={catalog}
        issues={issues} path={`${path}.${child.name}`} connection={connection} onChange={next => onChange({ ...object, [child.name]: next })} />
      {!field.fields?.some(known => known.name === child.name) && <button type="button" className="link is-muted" onClick={() => {
        const next = { ...object }; delete next[child.name]; setExtraFields(current => current.filter(item => item.name !== child.name)); onChange(next);
      }}>{t("scenarios.remove")}</button>}
    </div>)}
      {field.open && <AddObjectField names={fields.map(f => f.name)} onAdd={child => { setExtraFields([...extraFields, child]); onChange({ ...object, [child.name]: initialLiteral(child) }); }} />}
    </CompoundValue>;
  }
  if (field.type === "array" && field.items) {
    const items = Array.isArray(value) ? value : [];
    return <CompoundValue title={field.title} error={error}>{items.map((item, index) => <div className="scenario-bound-field" key={index}><ConstantValue
      field={{ ...field.items!, title: field.items!.title || t("scenarios.array_item"), secret: field.secret || field.items!.secret }} value={item} catalog={catalog}
      issues={issues} path={`${path}.${index}`} connection={connection} onChange={next => onChange(items.map((v, i) => i === index ? next : v))} />
      <button type="button" className="link is-muted" onClick={() => onChange(items.filter((_, i) => i !== index))}>{t("scenarios.remove")}</button></div>)}
      <button type="button" className="link" onClick={() => onChange([...items, initialLiteral(field.items!)])}>{t("scenarios.add_item")}</button></CompoundValue>;
  }
  if (field.type === "lookup") return <LookupValue field={field} value={value} connection={connection} onChange={onChange} error={error} />;
  if (field.type === "enum") return <><SelectField label={field.title} invalid={Boolean(error)} value={String(field.options?.findIndex(option => option.value === value) ?? -1)}
    options={[["-1", t("scenarios.select")], ...(field.options ?? []).map((option, index) => [String(index), option.label] as [string, string])]}
    onChange={index => onChange(field.options?.[Number(index)]?.value)} wide /><FieldError error={error} /></>;
  const Control = fieldControl({ ...field, control: field.control.startsWith("lookup@") ? "" : field.control });
  if (Control) return <><Control field={field} value={value} disabled={false} error={error} onChange={onChange} />
    {field.nullable && <div className="scenario-toggle"><span>{t("scenarios.nullable")}</span><SwitchButton className="ui-switch is-compact"
      label={t("scenarios.nullable")} checked={value === null} onClick={() => onChange(value === null ? "" : null)} /></div>}</>;
  return <FormField label={field.title} value="" disabled error={t("scenarios.control_unavailable")} wide />;
}
