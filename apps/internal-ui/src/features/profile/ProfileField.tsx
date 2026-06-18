export function ProfileField({ label, value, onChange, placeholder = "", type = "text", mono = false, disabled = false }: { label: string; value: string; onChange?: (value: string) => void; placeholder?: string; type?: "text" | "password"; mono?: boolean; disabled?: boolean }) {
  return (
    <label className="readonly-field">
      <span>{label}</span>
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} onChange={(event) => onChange?.(event.target.value)} />
    </label>
  );
}
