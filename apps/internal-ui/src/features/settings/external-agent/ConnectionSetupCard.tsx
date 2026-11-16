import { useState } from "react";
import { FormField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { StatusPill } from "../../../shared/ui";
import { ServiceAlert } from "../../integrations/services/connect/ServiceAlert";
import { et } from "./copy";
import type { AccessDraft } from "./model";

export function ConnectionSetupCard({ busy, failed, save }: {
  busy: boolean; failed: boolean; save: (draft: AccessDraft, after?: "key" | "check") => Promise<boolean>;
}) {
  const [draft, setDraft] = useState<AccessDraft>({ name: "", baseUrl: "", outboundKey: "" });
  const valid = Object.values(draft).every(value => value.trim());
  const change = (key: keyof AccessDraft) => (value: string) => setDraft(current => ({ ...current, [key]: value }));
  return <section className="administration-card" data-connection-form aria-busy={busy}>
    <div className="service-connect-fields"><div className="settings-card-head service-card-title">
      <div><strong>{et("setup.connectionTitle")}</strong></div><StatusPill status="unchecked" label={et("setup.notConfigured")} /></div>
      <div className="administration-fields"><FormField label={et("setup.connectionName")} value={draft.name} onChange={change("name")} disabled={busy} />
        <FormField label={et("setup.serviceUrl")} value={draft.baseUrl} placeholder="https://…" mono onChange={change("baseUrl")} disabled={busy} /></div>
      <section className="service-connect-fields"><div className="settings-card-head"><div><strong>{et("setup.outgoingTitle")}</strong><small>{et("setup.outgoingHelp")}</small></div></div>
        <div className="service-field"><FormField label={et("setup.outgoingKey")} value={draft.outboundKey} type="password" mono onChange={change("outboundKey")} disabled={busy} />
          <small>{et("setup.outgoingKeyHint")}</small></div>
        <p className="service-connect-note">{et("setup.checkHint")}</p>
        <div className="settings-card-actions"><Button variant="secondary" disabled={busy || !valid} onClick={() => void save(draft, "check")}>{et("setup.checkConnection")}</Button></div>
      </section>
      <section className="service-connect-fields"><div className="settings-card-head"><div><strong>{et("setup.incomingTitle")}</strong><small>{et("setup.incomingHelp")}</small></div></div>
        <span data-incoming-key-state="absent"><StatusPill status="unchecked" label={et("setup.keyAbsent")} /></span><p className="service-connect-note">{et("setup.incomingKeyHint")}</p>
        <div className="settings-card-actions"><Button variant="secondary" disabled={busy} onClick={() => void save(draft, "key")}>{et("setup.createKey")}</Button></div>
      </section>
    </div>
    {failed && <div className="external-setup-error" role="alert"><ServiceAlert tone="error" title={et("feedback.saveErrorTitle")} text={et("feedback.saveErrorHelp")} /></div>}
    <div className="administration-actions"><Button variant="primary" disabled={busy || !valid} onClick={() => void save(draft)}>{et("setup.saveConnection")}</Button></div>
  </section>;
}
