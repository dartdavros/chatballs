import { useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { et } from "./copy";

export function NewlyCreatedKey({ value, close }: { value: string; close: () => void }) {
  const [state, setState] = useState<"idle" | "copying" | "copied" | "error">("idle");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; clearTimeout(timer.current); }; }, []);
  async function copy() {
    if (state === "copying") return;
    clearTimeout(timer.current); setState("copying");
    try {
      await navigator.clipboard.writeText(value);
      if (!mounted.current) return;
      setState("copied"); timer.current = setTimeout(() => setState("idle"), 3000);
    } catch { if (mounted.current) setState("error"); }
  }
  const label = state === "copied" ? t("common.copied") : state === "error" ? et("feedback.copyKeyError")
    : state === "copying" ? et("feedback.copyingKey") : et("policy.copyKey");
  return <section className="administration-card" data-new-key-once>
    <div className="settings-card-head"><div><strong>{et("policy.newKey")}</strong><small>{et("policy.newKeyLead")}</small></div></div>
    <div className="employee-password-field"><span>{et("settings.incoming")}</span><span className="employee-password-value"><code>{value}</code>
      <button type="button" className={`ui-icon-button is-bare ea-key-copy${state === "copied" ? " is-copied" : ""}`}
        aria-label={label} title={label} aria-busy={state === "copying"} disabled={state === "copying"} onClick={() => void copy()}>
        <Icon name={state === "copied" ? "check" : "copy"} size={18} strokeWidth={1.8} /></button></span></div>
    <div className="administration-actions"><Button variant="primary" onClick={close}>{et("policy.keyDone")}</Button></div>
  </section>;
}
