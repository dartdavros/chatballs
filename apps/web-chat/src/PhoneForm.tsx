import { useState } from "react";
import { t } from "./i18n";
import { widgetClasses as classes } from "./widgetClasses";
import { formatPhone } from "./phoneFormat";

export function PhoneForm({ accent, onSubmit }: { accent: string; onSubmit: (phone: string) => Promise<boolean> }) {
  const [phone, setPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);
  const valid = phone.replace(/\D/g, "").length === 11;
  async function submit() { if (!valid || sending) return; setSending(true); setError(false); const ok = await onSubmit(phone); setSending(false); if (!ok) setError(true); }
  return <div className={classes.form} style={{ "--cb-accent": accent } as React.CSSProperties}><input type="tel" inputMode="tel" value={phone} onChange={(event) => setPhone(formatPhone(event.target.value))} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void submit(); } }} placeholder="+7 (___) ___-__-__" className={classes.formField} aria-invalid={error} /><button type="button" onClick={() => void submit()} disabled={!valid || sending} className={classes.formSubmit} data-valid={valid}>{sending ? t("chat.sending") : t("chat.share_number")}</button>{error && <div style={{ marginTop: 6, color: "var(--cb-required, #cf1322)", fontSize: 11.5 }}>{t("chat.share_number_failed")}</div>}</div>;
}

