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

type SelectFieldProps = {
  /** Метка перед значением: цветная точка группы на карточке агента. */
  adornment?: ReactNode;
  disabled?: boolean;
  invalid?: boolean;
  label: string;
  onChange: (value: string) => void;
  options: Array<[string, string]>;
  /** Нет прав на правку: вместо селекта значение показывается текстом. */
  readOnly?: boolean;
  /** Текст для режима без прав, когда значения нет в списке: список вариантов
   *  грузят только тем, кто может править. */
  readOnlyText?: string;
  value: string;
  wide?: boolean;
};

/** Селект приложения — один на всё: подпись, бокс поля и шеврон. Точку перед
 *  значением и режим без прав правки держит `.select-box`: рамка тогда на нём,
 *  а сам селект внутри без рамки и фона. */
export function SelectField({ adornment, disabled = false, invalid = false, label, onChange, options, readOnly = false, readOnlyText, value, wide = false }: SelectFieldProps) {
  const className = ["readonly-field", "select-like", invalid ? "is-invalid" : "", readOnly ? "is-readonly" : "", wide ? "wide" : ""].filter(Boolean).join(" ");
  const control = readOnly
    ? <span className="select-value">{readOnlyText ?? options.find(([optionValue]) => optionValue === value)?.[1] ?? ""}</span>
    : (
      <select disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, labelText]) => <option value={optionValue} key={optionValue}>{labelText}</option>)}
      </select>
    );
  const chevron = <Icon name="chevron" size={14} strokeWidth={2.2} />;
  const boxed = Boolean(adornment) || readOnly;

  return (
    <label className={className}>
      <span>{label}</span>
      {boxed ? <span className="select-box">{adornment}{control}{chevron}</span> : <>{control}{chevron}</>}
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
