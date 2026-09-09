import type { ReactNode } from "react";

import { Icon } from "./icons";

type FormFieldProps = {
  disabled?: boolean;
  error?: string;
  label: string;
  mono?: boolean;
  onChange?: (value: string) => void;
  placeholder?: string;
  type?: "password" | "text";
  value: string;
  wide?: boolean;
};

export function FormField({
  disabled = false,
  error,
  label,
  mono = false,
  onChange,
  placeholder = "",
  type = "text",
  value,
  wide = false,
}: FormFieldProps) {
  const editable = Boolean(onChange) && !disabled;
  const className = [
    "readonly-field",
    "form-field",
    editable ? "is-editable" : "is-readonly",
    disabled ? "is-disabled" : "",
    error ? "is-invalid" : "",
    wide ? "wide" : "",
  ].filter(Boolean).join(" ");

  return (
    <label className={className}>
      <span>{label}</span>
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} readOnly={!editable} onChange={(event) => onChange?.(event.target.value)} />
      {error && <small className="form-field-error" role="alert">{error}</small>}
    </label>
  );
}

// hint — пояснение под полем: у части настроек выбор непонятен без одной
// фразы («Как в установке» — это какой?), а класть её отдельным абзацем рядом
// значит оторвать от поля, к которому она относится.
export function SelectField({ disabled = false, label, value, onChange, options, hint }: { disabled?: boolean; label: string; value: string; onChange: (value: string) => void; options: Array<[string, string]>; hint?: string }) {
  return (
    <label className="readonly-field select-like">
      <span>{label}</span>
      <select disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, labelText]) => <option value={optionValue} key={optionValue}>{labelText}</option>)}
      </select>
      <Icon name="chevron" size={14} />
      {hint && <small className="form-field-hint">{hint}</small>}
    </label>
  );
}

export function TextAreaField({ disabled = false, label, value, onChange }: { disabled?: boolean; label: string; value: string; onChange: (value: string) => void }) {
  const className = ["readonly-field", "form-field", "wide", disabled ? "is-readonly is-disabled" : "is-editable"].join(" ");
  return (
    <label className={className}>
      <span>{label}</span>
      <textarea value={value} disabled={disabled} readOnly={disabled} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

export function SwitchButton({ checked, onClick, className, label, disabled = false }: { checked: boolean; onClick: () => void; className: string; label: string; disabled?: boolean }) {
  return <button className={`${className}${checked ? " on" : ""}`} type="button" role="switch" aria-checked={checked} aria-label={label} onClick={onClick} disabled={disabled}><i /></button>;
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return <div className="key-value"><span>{label}</span><strong>{value}</strong></div>;
}

export function MetricBox({ label, value }: { label: string; value: ReactNode }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
