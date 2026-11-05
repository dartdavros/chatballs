import { fmt, t } from "../../../../i18n";
import { SelectField } from "../../../../shared/form-controls";
import { fieldControl, type ControlProps } from "./fieldControls";
import { StructuredObjectEntry } from "./StructuredObjectEntry";
import { emptyValue, jsonField, replaceEntry, valueKind, type ValueKind } from "./structuredValues";

/** Baseline constant-values: typed fields and lists, with no required code editor. */
export function StructuredValue({ field, value, disabled, error, onChange }: ControlProps) {
  const kind = valueKind(value);
  const kinds: ValueKind[] = ["string", "number", "boolean", "object", "array", ...(field.nullable ? ["null" as const] : [])];
  const options: Array<[string, string]> = kinds.map(type =>
    [type, t(type === "null" ? "scenarios.empty_value" : `scenarios.type_${type}`)]);
  const label = field.title || t("scenarios.source_constant");
  const scalar = { ...field, type: kind, control: kind === "string" && !field.secret ? "textarea@1" : "", nullable: false };
  const Control = !["object", "array", "null"].includes(kind) ? fieldControl(scalar) : undefined;
  const object = kind === "object" ? value as Record<string, unknown> : {};
  const items = kind === "array" ? value as unknown[] : [];
  return <div className="scenario-bound-field" role="group" aria-label={label}>
    <SelectField label={t("skill_templates.type")} value={kind} options={options} disabled={disabled}
      invalid={Boolean(error)} onChange={next => onChange(emptyValue(next))} wide />
    {Control && <Control field={{ ...scalar, title: label }} value={value} disabled={disabled} error={error} onChange={onChange} />}
    {kind === "object" && <>
      {Object.entries(object).map(([name, child], index) => <StructuredObjectEntry key={index} name={name}
        names={Object.keys(object)} disabled={disabled} rename={next => onChange(replaceEntry(object, index, next, child))}
        remove={() => onChange(Object.fromEntries(Object.entries(object).filter((_, i) => i !== index)))}>
        <StructuredValue field={{ ...jsonField(name, t("scenarios.source_constant")), secret: field.secret }} value={child} disabled={disabled}
          onChange={next => onChange(replaceEntry(object, index, name, next))} />
      </StructuredObjectEntry>)}
      <button type="button" className="link" disabled={disabled || Object.hasOwn(object, "")}
        onClick={() => onChange({ ...object, "": "" })}>{t("scenarios.add_field")}</button>
    </>}
    {kind === "array" && <>
      {items.map((item, index) => <div className="scenario-bound-children" key={index}>
        <StructuredValue field={{ ...jsonField(String(index), `${t("scenarios.array_item")} · ${fmt.number(index + 1)}`), secret: field.secret }}
          value={item} disabled={disabled} onChange={next => onChange(items.map((child, i) => i === index ? next : child))} />
        <button type="button" className="link" disabled={disabled}
          onClick={() => onChange(items.filter((_, i) => i !== index))}>{t("scenarios.remove")}</button>
      </div>)}
      <button type="button" className="link" disabled={disabled}
        onClick={() => onChange([...items, ""])}>{t("scenarios.add_item")}</button>
    </>}
  </div>;
}
