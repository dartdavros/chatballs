import { useState } from "react";
import { Icon } from "../../../shared/icons";
import { et } from "../../settings/external-agent/copy";
import { FeatureCard } from "../../settings/external-agent/FeatureCard";
import { SettingsLoadState } from "../../settings/external-agent/SettingsLoadState";
import { SettingsConfirmation } from "../../settings/external-agent/SettingsConfirmation";
import { NewlyCreatedKey } from "../../settings/external-agent/NewlyCreatedKey";
import { ConnectionSetupCard } from "../../settings/external-agent/ConnectionSetupCard";
import { ConnectionSettings } from "../../settings/external-agent/ConnectionSettings";
import { useExternalAgentSettings } from "../../settings/external-agent/useExternalAgentSettings";
import "../../settings/external-agent/styles.css";

export function ExternalAgentSettings({ organization }: { organization: string }) {
  const state = useExternalAgentSettings(organization);
  const [disabling, setDisabling] = useState(false);
  const settings = state.settings;
  if (state.forbidden) return <div className="external-settings is-configured"><section className="administration-card" style={{ minHeight: 440 }} data-settings-permission="denied">
    <div className="settings-card-head"><div><strong>{et("settings.readonly")}</strong></div></div>
    <div className="settings-risk-note" role="alert"><Icon name="lock" size={16} /><p>{et("settings.readonlyHelp")}</p></div>
  </section></div>;
  if (!settings || state.failed) return <div className="external-settings is-configured"><SettingsLoadState failed={state.failed} reload={() => void state.reload()} /></div>;
  const retained = settings.connections.length > 0;
  const review = settings.enabled && settings.connections.some(connection => connection.bindings.some(binding => !binding.policyAccepted));
  return <div className={`external-settings${retained ? " is-configured" : ""}`}>
    <FeatureCard enabled={settings.enabled} retained={retained} review={review}
      busy={state.busy} failed={state.featureFailure}
      onToggle={() => { if (settings.enabled) setDisabling(true); else void state.feature(true); }} />
    {state.incomingKey && <NewlyCreatedKey value={state.incomingKey} close={state.dismissKey} />}
    {settings.connections.map(connection => <ConnectionSettings key={connection.id} organization={organization} connection={connection}
      catalog={settings.catalog} enabled={settings.enabled} state={state} />)}
    {settings.enabled && !settings.connections.length && <ConnectionSetupCard busy={state.busy} failed={!state.featureFailure && (state.error === "save" || state.error === "check")} save={state.create} />}
    {disabling && <SettingsConfirmation action="disable" busy={state.busy} cancel={() => { if (!state.busy) setDisabling(false); }}
      confirm={() => void state.feature(false).then(ok => { if (ok) setDisabling(false); })} />}
  </div>;
}
