import { useState } from "react";
import { t } from "../../../i18n";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Button, CopyButton } from "../../../shared/ui-controls";
import type { ExternalKey } from "./types";

export function ExternalKeyFields({ value, disabled, rotate }: { value?: ExternalKey; disabled: boolean; rotate: () => Promise<void> }) {
  const [confirming, setConfirming] = useState(false);
  if (!value) return <p className="scenario-banner">{t("scenarios.key_pending")}</p>;
  const example = `curl -X POST '${value.url}' -H 'Authorization: Bearer ${value.key ?? "<key>"}' -H 'Idempotency-Key: <request-id>' -H 'Content-Type: application/json' -d '{"parameters":{}}'`;
  return <div className="scenario-form">
    <label className="scenario-copy-field"><span>{t("scenarios.api_address")}</span><div><code>{value.url}</code><CopyButton value={value.url} label={t("common.copy")} /></div></label>
    <label className="scenario-copy-field"><span>{t("scenarios.api_key")}</span><div><code>{value.key ?? "••••••••••••••••••••"}</code>
      {value.key && <CopyButton value={value.key} label={t("common.copy")} />}</div></label>
    <p className="scenario-note">{t(value.key ? "scenarios.key_fresh" : "scenarios.key_hidden")}</p>
    <button type="button" className="link" disabled={disabled} onClick={() => setConfirming(true)}>{t("scenarios.key_rotate")}</button>
    <label className="scenario-copy-field"><span>{t("scenarios.api_example")}</span><pre>{example}</pre><CopyButton value={example} label={t("common.copy")} /></label>
    <DecisionDialog open={confirming} onClose={() => setConfirming(false)} tone="warning" icon="warning"
      title={t("scenarios.key_rotate_title")} description={t("scenarios.key_rotate_text")}
      actions={<><Button variant="secondary" onClick={() => setConfirming(false)}>{t("scenarios.cancel")}</Button>
        <Button variant="primary" disabled={disabled} onClick={async () => { await rotate(); setConfirming(false); }}>{t("scenarios.key_rotate")}</Button></>} />
  </div>;
}
