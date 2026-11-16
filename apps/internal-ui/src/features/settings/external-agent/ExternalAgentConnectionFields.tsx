import type { Ref } from "react";
import { tn } from "../../../i18n";
import { FormField, SwitchButton } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { StatusPill } from "../../../shared/ui";
import { HelpTitle } from "./HelpTitle";
import { et } from "./copy";
import { CapabilitiesResult } from "./CapabilitiesResult";
import { SavedAccessFields } from "./SavedAccessFields";
import type { ConnectionDraft } from "./model";

export function ExternalAgentConnectionFields({ sectionRef, connection, disabled, retained, review, checking, failed, failure, dirty, accessDirty, change, check, keyAction }: {
  sectionRef?: Ref<HTMLElement>;
  connection: ConnectionDraft; disabled: boolean; retained: boolean; review: boolean; checking: boolean; failed: boolean;
  failure: "access" | "unavailable" | "incompatible"; dirty: boolean; accessDirty: boolean;
  change: (patch: Partial<ConnectionDraft>) => void; check: () => void; keyAction: (action: "create" | "rotate" | "revoke") => void;
}) {
  const inactive = !connection.enabled;
  const names = connection.bindings.map(binding => binding.agentName);
  const disabledHelp = names.length ? tn("external.settings.connectionDisabledLead", names.length, { agents: names.join(" · ") }) : et("settings.disabledLead");
  const displayFailure = failed && !retained;
  const status = inactive || retained ? "archived" : checking ? "pending" : displayFailure ? "error" : review ? "pending" : connection.compatible ? "healthy" : "unchecked";
  const statusKey = inactive ? "connectionDisabled" : retained ? "statusRetained" : checking ? "statusChecking" : displayFailure ? "statusError"
    : review ? "statusReview" : connection.compatible ? "statusReady" : "statusReview";
  return <section ref={sectionRef} className="administration-card" data-connection-active={!inactive}
    data-connection-check={inactive ? "disabled" : retained ? "retained" : checking ? "pending" : displayFailure ? "failed" : review ? "review-required" : "ready"}>
    <div className="settings-card-head"><div><HelpTitle title={et("settings.connection")} topic="keys" /></div>
      <StatusPill status={status} label={et(`settings.${statusKey}`)} /></div>
    {inactive && <div className="service-connection-access" data-connection-disabled><div><strong>{et("settings.connectionActive")}</strong></div>
      <SwitchButton className="ui-switch" checked={false} disabled={disabled} label={et("settings.connectionActive")} onClick={() => change({ enabled: true })} /></div>}
    <div className="administration-fields">
      <FormField label={et("settings.name")} value={connection.name} disabled={disabled} onChange={name => change({ name })} />
      <FormField label={et("settings.address")} value={connection.baseUrl} mono disabled={disabled} onChange={baseUrl => change({ baseUrl })} />
      <SavedAccessFields connection={connection} disabled={disabled} checking={checking} dirty={dirty} change={change} keyAction={keyAction} />
    </div>
    <div className="administration-actions"><Button variant="secondary" disabled={disabled || checking || accessDirty || inactive} onClick={check}>
      {et(checking ? "settings.checking" : "settings.check")}</Button></div>
    <CapabilitiesResult checking={checking} failed={displayFailure} failure={failure} compatible={connection.compatible}
      enabled={!inactive} retained={retained} review={review} disabledHelp={disabledHelp} />
  </section>;
}
