import { t } from "../../i18n";

export function AuthCodeInput({ value, onChange, error = false, autoFocus = false }: { value: string; onChange: (value: string) => void; error?: boolean; autoFocus?: boolean }) {
  const activeIndex = Math.min(value.length, 5);
  const digits = value.padEnd(6, " ").slice(0, 6).split("");
  return (
    <div className="auth-code-input-wrap">
      <div className="auth-code-cells">
        {digits.map((digit, index) => {
          const filled = digit.trim().length > 0;
          const active = !error && index === activeIndex && value.length < 6;
          return <span className={`${filled ? "filled" : ""} ${active ? "active" : ""} ${error ? "error" : ""}`} key={index}>{digit}</span>;
        })}
      </div>
      <input
        className="auth-code-input-hidden"
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        maxLength={6}
        autoFocus={autoFocus}
        aria-label={t("admin.code_from_authenticator_app")}
      />
    </div>
  );
}
