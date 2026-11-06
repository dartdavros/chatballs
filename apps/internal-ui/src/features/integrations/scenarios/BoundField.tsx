import { useState } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import type { ServiceField } from "../services/types";
import { compatibleField, valueOptions } from "./bindingOptions";
import { ConstantValue } from "./ConstantValue";
import { AddObjectField } from "./AddObjectField";
import { inferredField, initialBound, initialLiteral } from "./valueFields";
import { id } from "./model";
import { sameReference } from "./referenceModel";
import type { Binding, BindingSource, BoundValue, DataSchema, EditorCatalog, ScenarioDocument, Issue } from "./types";

type Props = { field: ServiceField; value?: BoundValue; connection: string; current: string;
  document: ScenarioDocument; catalog: EditorCatalog; onChange: (value: BoundValue | undefined) => void;
  onInput: (name: string, schema: DataSchema) => void; error?: string; issues?: Issue[]; path?: string };

export function fieldSchema(field: ServiceField): DataSchema {
  return { type: field.type as DataSchema["type"], title: field.title, required: field.required, nullable: field.nullable,
    ...(field.open ? { open: true } : {}),
    ...(field.fields ? { properties: Object.fromEntries(field.fields.map(child => [child.name, fieldSchema(child)])) } : {}),
    ...(field.items ? { items: fieldSchema(field.items) } : {}), ...(field.options ? { options: field.options.map(o => o.value) } : {}),
    ...(field.lookup ? { lookup: field.lookup } : {}) };
}
function isBinding(value: BoundValue | undefined): value is Binding {
  return Boolean(value && !Array.isArray(value) && typeof value === "object" && typeof value.source === "string");
}
export function BoundField(props: Props) {
  const { field, value, connection, current, document, catalog, onChange, onInput, issues = [], path = field.name } = props;
  const error = props.error ?? issues.find(issue => issue.path.replace(/\.\$$/, "") === path)?.message;
  const binding = isBinding(value) ? value : undefined;
  const [extraFields, setExtraFields] = useState<ServiceField[]>([]);
  const source = binding?.source === "constant" && binding.value === null && field.nullable ? "null" : binding?.source ?? (value === undefined ? "none" : "constant");
  const options = valueOptions(document, catalog, current).filter(option => compatibleField(option.field, field) || catalog.transforms.some(transform =>
    transform.inputTypes.includes(option.field.type) && (transform.outputType === field.type || transform.outputType === "any")));
  const kinds = [...new Set(options.map(option => option.binding.source))];
  function selectSource(next: string) {
    if (next === "none") { onChange(undefined); return; }
    if (next === "null") { onChange({ source: "constant", value: null }); return; }
    if (next === "constant") { onChange(field.type === "object" && !field.control ? {} : field.type === "array" && !field.control ? [] : { source: "constant", value: initialLiteral(field) }); return; }
    if (next === "input") {
      const name = `input_${id()}`; onInput(name, fieldSchema(field)); onChange({ source: "input", name }); return;
    }
    const option = options.find(item => item.binding.source === next); if (option) onChange(option.binding);
  }
  function child(name: string, next: BoundValue | undefined) {
    const object = value && !isBinding(value) && !Array.isArray(value) ? { ...value } : {};
    if (next === undefined) delete object[name]; else object[name] = next;
    onChange(object);
  }
  const sources: Array<[string, string]> = [["none", t("scenarios.source_none")], ["constant", t("scenarios.source_constant")],
    ...(field.nullable ? [["null", t("scenarios.nullable")] as [string, string]] : []), ["input", t("scenarios.source_input")],
    ...kinds.map(kind => [kind, t(`scenarios.source_${kind as BindingSource}`)] as [string, string])];
  if (binding && !sources.some(([key]) => key === source)) sources.push([source, t(`scenarios.source_${binding.source}`)]);
  const selected = binding ? options.find(option => sameReference(option.binding, binding)) : undefined;
  const transforms = catalog.transforms.filter(transform => transform.inputTypes.includes(selected?.field.type ?? field.type)
    && (transform.outputType === field.type || transform.outputType === "any"));
  const transform = catalog.transforms.find(transform => transform.key === binding?.transform);
  const objectFields = [...(field.fields ?? []), ...extraFields];
  if (value && !isBinding(value) && !Array.isArray(value)) for (const [name, child] of Object.entries(value)) {
    if (!objectFields.some(f => f.name === name)) objectFields.push(inferredField(name, isBinding(child) ? child.value : child));
  }
  return <div className="scenario-bound-field">
    <SelectField label={field.title} value={source} options={sources} onChange={selectSource} invalid={Boolean(error)} wide />
    {source === "constant" && field.type === "object" && !field.control && <div className="scenario-bound-children">
      {objectFields.map(nested => <BoundField key={nested.name} {...props} field={{ ...nested, secret: field.secret || nested.secret }}
        error={undefined} path={`${path}.${nested.name}`}
        value={value && !isBinding(value) && !Array.isArray(value) ? value[nested.name] : undefined} onChange={next => child(nested.name, next)} />)}
      {field.open && <AddObjectField names={objectFields.map(f => f.name)} onAdd={nested => { setExtraFields([...extraFields, nested]); child(nested.name, initialBound(nested)); }} />}
    </div>}
    {source === "constant" && field.type === "array" && field.items && !field.control && <div className="scenario-bound-children">
      {(Array.isArray(value) ? value : []).map((item, index) => <div key={index}>
        <BoundField {...props} field={{ ...field.items!, title: field.items!.title || t("scenarios.array_item"), secret: field.secret || field.items!.secret }} value={item}
          error={undefined} path={`${path}.${index}`}
          onChange={next => { const items = Array.isArray(value) ? [...value] : []; if (next === undefined) items.splice(index, 1); else items[index] = next; onChange(items); }} />
      </div>)}
      <button type="button" className="link has-icon" onClick={() => onChange([...(Array.isArray(value) ? value : []), { source: "constant", value: "" }])}>
        <Icon name="plus" size={14} />{t("scenarios.add_item")}</button>
    </div>}
    {source === "constant" && (field.control || !["object", "array"].includes(field.type)) && <ConstantValue field={field} value={binding?.value} connection={connection} catalog={catalog}
      issues={issues} path={path}
      onChange={next => onChange({ ...binding, source: "constant", value: next })} />}
    {source === "input" && binding && <FormField label={t("scenarios.inputs")} value={document.parameters.properties?.[binding.name ?? ""]?.title ?? field.title}
      onChange={title => onInput(binding.name!, { ...fieldSchema(field), title })} wide />}
    {source !== "constant" && source !== "null" && source !== "none" && source !== "input" && <SelectField label={t("scenarios.field")} value={selected?.key ?? ""}
      options={[["", t("scenarios.select")], ...options.filter(option => option.binding.source === source).map(option => [option.key, option.label] as [string, string])]}
      onChange={key => { const option = options.find(item => item.key === key); if (option) onChange(option.binding); }} wide />}
    {binding && source !== "null" && transforms.length > 0 && <SelectField label={t("scenarios.transform")} value={binding.transform ?? ""}
      options={[["", t("scenarios.no_transform")], ...transforms.map(transform => [transform.key, transform.title] as [string, string])]}
      onChange={key => { const next = { ...binding }; if (key) { next.transform = key; next.args = {}; } else { delete next.transform; delete next.args; } onChange(next); }} wide />}
    {binding && transform && <ConstantValue field={transform.arguments} value={binding.args ?? {}} connection={connection} catalog={catalog}
      onChange={args => onChange({ ...binding, args: args as Record<string, unknown> })} />}
    {error && source !== "constant" && <span className="scenario-field-error" role="alert">{error}</span>}
  </div>;
}
