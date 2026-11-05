import type { ComponentType } from "react";

import { FormField, SelectField, SwitchButton, TextAreaField } from "../../../../shared/form-controls";
import type { ServiceField } from "../types";
import { StructuredValue } from "./StructuredValue";
import { ScenarioSettingsValue } from "../../scenarios/ScenarioSettingsValue";

export type ServiceValues = Record<string, unknown>;
export type ControlProps = {
  field: ServiceField;
  value: unknown;
  error?: string;
  disabled: boolean;
  onChange: (value: unknown) => void;
};

const text = (value: unknown) => typeof value === "string" || typeof value === "number" || typeof value === "boolean" ? String(value) : "";

function InputControl({ field, value, error, disabled, onChange }: ControlProps) {
  const secret = field.control.startsWith("secret@") || (field.secret && !field.control.startsWith("url@"));
  const numeric = field.type === "integer" || field.type === "number";
  const type = secret ? "password" : numeric ? "number"
    : field.type === "date" ? "date" : field.type === "datetime" ? "datetime-local" : "text";
  return <FormField label={field.title} value={text(value)} error={error} placeholder={field.placeholder} disabled={disabled}
    mono={field.control.startsWith("url@") || field.secret} type={type} wide onChange={(next) => {
      onChange(numeric && next !== "" && Number.isFinite(Number(next)) ? Number(next) : next);
    }} />;
}

function TextControl({ field, value, disabled, onChange }: ControlProps) {
  return <TextAreaField label={field.title} value={text(value)} disabled={disabled} onChange={onChange} />;
}

function SelectControl({ field, value, error, disabled, onChange }: ControlProps) {
  const selected = field.options?.findIndex((option) => option.value === value) ?? -1;
  return <SelectField label={field.title} value={selected < 0 ? "" : String(selected)} disabled={disabled} invalid={Boolean(error)} wide
    options={(field.options ?? []).map((option, index) => [String(index), option.label])}
    onChange={(next) => onChange(field.options?.[Number(next)]?.value)} />;
}

function ToggleControl({ field, value, disabled, onChange }: ControlProps) {
  return <div className="readonly-field"><span>{field.title}</span>
    <SwitchButton className="ui-switch" label={field.title} checked={value === true} disabled={disabled} onClick={() => onChange(value !== true)} />
  </div>;
}

// Доверенный frontend-пакет регистрирует свой компонент до открытия формы.
// Незнакомый ключ/версия никогда не превращается в текстовый input.
const controls = new Map<string, ComponentType<ControlProps>>([
  ["scenario_settings@1", ScenarioSettingsValue],
  ["structured_value@1", StructuredValue],
  ...["text", "url", "secret", "number", "date"].map((key) => [`${key}@1`, InputControl] as const),
  ["textarea@1", TextControl], ["select@1", SelectControl], ["toggle@1", ToggleControl],
]);

export function registerFieldControl(ref: string, component: ComponentType<ControlProps>) {
  if (!/^[a-z][a-z0-9_.]*@[1-9]\d*$/.test(ref) || controls.has(ref)) throw new Error(`Invalid or duplicate service control: ${ref}`);
  controls.set(ref, component);
}

export function fieldControl(field: ServiceField) {
  const defaults: Record<string, string> = {
    json: "structured_value@1",
    string: field.secret ? "secret@1" : "text@1", integer: "number@1", number: "number@1",
    boolean: "toggle@1", enum: "select@1", date: "date@1", datetime: "date@1",
  };
  return controls.get(field.control || defaults[field.type]);
}

export function unsupportedFields(fields: ServiceField[]) {
  return fields.some((field) => !fieldControl(field));
}
