import { useEffect, useState } from "react";
import { FormField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { StatusPill } from "../../../shared/ui";
import { et } from "./copy";
import type { ConnectionDraft } from "./model";

export function SavedAccessFields({ connection, disabled, checking, dirty, change, keyAction }: {
  connection: ConnectionDraft; disabled: boolean; checking: boolean; dirty: boolean;
  change: (patch: Partial<ConnectionDraft>) => void; keyAction: (action: "create" | "rotate" | "revoke") => void;
}) {
  const [replacing, setReplacing] = useState(false);
  useEffect(() => setReplacing(false), [connection.revision]);
  return <>
    <div className="service-connect-stack ea-key-field" data-saved-secret="outgoing">
      <FormField label={et("settings.outgoing")} value={connection.outboundKey ?? ""} type="password" mono
        placeholder={replacing ? "" : "••••••••••••"} disabled={disabled || !replacing} onChange={outboundKey => change({ outboundKey })} />
      <small className="settings-section-note">{et(replacing ? "setup.outgoingKeyHint" : "settings.stored")}</small>
      <div className="ea-key-actions"><Button variant="secondary" icon="refresh" disabled={disabled || checking}
        onClick={() => setReplacing(true)}>{et("settings.replace")}</Button></div>
    </div>
    <div className="service-connect-stack ea-key-field" data-saved-secret="incoming">
      {connection.keyConfigured ? <>
        <FormField label={et("settings.incoming")} value="" placeholder="••••••••••••" type="password" disabled />
        <small className="settings-section-note">{et("settings.stored")}</small>
        <div className="ea-key-actions"><Button variant="secondary" icon="refresh" disabled={disabled || checking || dirty}
          onClick={() => keyAction("rotate")}>{et("settings.replace")}</Button>
          <Button variant="danger-outline" icon="xCircle" disabled={disabled || checking || dirty}
            onClick={() => keyAction("revoke")}>{et("settings.revoke")}</Button></div>
      </> : <>
        <span data-incoming-key-state="absent"><StatusPill status="unchecked" label={et("setup.keyAbsent")} /></span>
        <p className="service-connect-note">{et("setup.incomingKeyHint")}</p>
        <div className="ea-key-actions"><Button variant="secondary" disabled={disabled || checking || dirty}
          onClick={() => keyAction("create")}>{et("setup.createKey")}</Button></div>
      </>}
    </div>
  </>;
}
