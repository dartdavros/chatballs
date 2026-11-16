import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { ServiceAlert } from "../../integrations/services/connect/ServiceAlert";
import { et } from "./copy";

export function SettingsLoadState({ failed, reload }: { failed: boolean; reload: () => void }) {
  return <section className="administration-card" style={{ minHeight: 440 }} data-settings-load={failed ? "error" : "pending"}>
    <div className="settings-card-head"><div><strong>{et(failed ? "settings.title" : "settings.loading")}</strong></div></div>
    {failed ? <div className="external-load-error"><div role="alert"><ServiceAlert tone="error" title={et("settings.loadError")} text={et("settings.loadErrorHelp")} /></div>
      <div><Button variant="primary" onClick={reload}>{et("settings.retry")}</Button></div></div>
      : <LoadingState />}
  </section>;
}
