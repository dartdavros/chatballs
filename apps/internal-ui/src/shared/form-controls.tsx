import type { ReactNode } from "react";

import { Icon } from "./icons";

export function FormField({
  label,
  value,
  onChange,
  placeholder = "",
  type = "text",
  mono = false,
  wide = false,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  type?: "password" | "text";
  mono?: boolean;
  wide?: boolean;
  disabled?: boolean;
}) {
  return (
    <label className={`readonly-field ${wide ? "wide" : ""}`}>
      <span>{label}</span>
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} readOnly={!onChange} onChange={(event) => onChange?.(event.target.value)} />
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

export function SwitchButton({ checked, onClick, className, label, disabled = false }: { checked: boolean; onClick: () => void; className: string; label: string; disabled?: boolean }) {
  return <button className={`${className}${checked ? " on" : ""}`} type="button" role="switch" aria-checked={checked} aria-label={label} onClick={onClick} disabled={disabled}><i /></button>;
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return <div className="key-value"><span>{label}</span><strong>{value}</strong></div>;
}

export function MetricBox({ label, value }: { label: string; value: ReactNode }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
