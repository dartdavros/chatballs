import type { ReactNode } from "react";

import { Icon } from "./icons";

type FormFieldProps = {
  disabled?: boolean;
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
    wide ? "wide" : "",
  ].filter(Boolean).join(" ");

  return (
    <label className={className}>
      <span>{label}</span>
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} readOnly={!editable} onChange={(event) => onChange?.(event.target.value)} />
    </label>
  );
}

export function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: Array<[string, string]> }) {
  return (
    <label className="readonly-field select-like">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, labelText]) => <option value={optionValue} key={optionValue}>{labelText}</option>)}
      </select>
      <Icon name="chevron" size={14} />
    </label>
  );
}

export function TextAreaField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="readonly-field form-field is-editable wide">
      <span>{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
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
