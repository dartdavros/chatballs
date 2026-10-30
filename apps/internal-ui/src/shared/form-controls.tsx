import { useRef, useState, type ReactNode, type RefObject } from "react";

import { Icon } from "./icons";
import { SelectMenu } from "./ui-controls";

type FormFieldProps = {
  disabled?: boolean;
  error?: string;
  label: string;
  mono?: boolean;
  onChange?: (value: string) => void;
  /** Значение уходит на сервер по потере фокуса: запрос на каждую букву — это
   *  запрос на каждую букву. */
  onBlur?: () => void;
  placeholder?: string;
  type?: "number" | "password" | "text" | "date" | "time" | "datetime-local";
  value: string;
  wide?: boolean;
};

export function FormField({
  disabled = false,
  error,
  label,
  mono = false,
  onChange,
  onBlur,
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
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} readOnly={!editable} onChange={(event) => onChange?.(event.target.value)} onBlur={onBlur} />
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

/** Селект приложения — один на всё: подпись, бокс поля и шеврон. Список
 *  вариантов рисует общий `SelectMenu`, тот же, что у фильтров списков:
 *  нативного `<select>` в проекте нет нигде, иначе вместо меню приложения
 *  открывался бы список операционной системы. */
export function SelectField({ adornment, disabled = false, invalid = false, label, onChange, options, readOnly = false, readOnlyText, value, wide = false }: SelectFieldProps) {
  const [open, setOpen] = useState(false);
  const [menuWidth, setMenuWidth] = useState<number>();
  const trigger = useRef<HTMLButtonElement>(null);
  const className = ["readonly-field", "select-like", invalid ? "is-invalid" : "", readOnly ? "is-readonly" : "", disabled ? "is-disabled" : "", wide ? "wide" : ""].filter(Boolean).join(" ");
  const current = options.find(([optionValue]) => optionValue === value)?.[1] ?? "";
  const chevron = <Icon name="chevron" size={14} strokeWidth={2.2} />;

  if (readOnly) {
    return (
      <div className={className}>
        <span>{label}</span>
        <span className="select-box">{adornment}<span className="select-value">{readOnlyText ?? current}</span>{chevron}</span>
      </div>
    );
  }

  return (
    <div className={className}>
      <span>{label}</span>
      <SelectMenu
        disabled={disabled}
        onOpenChange={setOpen}
        onSelect={(next) => {
          onChange(next);
          setOpen(false);
        }}
        open={open}
        options={options.map(([optionValue, optionLabel]) => ({ value: optionValue, label: optionLabel }))}
        // Меню селекта равно ширине поля, а не фиксированным 216px фильтра.
        overlayClassName="app-dropdown is-field"
        overlayStyle={menuWidth ? { width: menuWidth } : undefined}
        selected={value ? [value] : []}
      >
        <button
          className="select-box"
          ref={trigger}
          type="button"
          aria-label={label}
          disabled={disabled}
          onClick={() => setMenuWidth(trigger.current?.offsetWidth)}
        >
          {adornment}
          <span className="select-value">{current}</span>
          {chevron}
        </button>
      </SelectMenu>
    </div>
  );
}

/** `inputRef` — для вставки в позицию курсора (переменные шаблона ответа). */
export function TextAreaField({ disabled = false, label, value, onChange, inputRef }: { disabled?: boolean; label: string; value: string; onChange: (value: string) => void; inputRef?: RefObject<HTMLTextAreaElement | null> }) {
  const className = ["readonly-field", "form-field", "wide", disabled ? "is-readonly is-disabled" : "is-editable"].join(" ");
  return (
    <label className={className}>
      <span>{label}</span>
      <textarea ref={inputRef} value={value} disabled={disabled} readOnly={disabled} onChange={(event) => onChange(event.target.value)} />
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
