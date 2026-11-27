import { useId, useState } from "react";

// X6/X8: подстановки подсвечены; при вводе работает обычное текстовое поле.
export function TemplateAddressField({ label, value, onChange, onBlur, disabled, invalid }: {
  label: string; value: string; onChange: (value: string) => void; onBlur?: () => void; disabled: boolean; invalid: boolean;
}) {
  const id = useId();
  const [focused, setFocused] = useState(false);
  return <div className={`server-template-field${invalid ? " is-invalid" : ""}`}>
    <input id={id} aria-label={label} aria-invalid={invalid} type="text" placeholder="https://" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}
      onFocus={() => setFocused(true)} onBlur={(event) => { event.target.scrollLeft = 0; setFocused(false); onBlur?.(); }} />
    {!focused && value && <div aria-hidden="true">{value.split(/(\{[^{}]*\})/).map((part, i) => /^\{/.test(part)
      ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>)}</div>}
  </div>;
}
