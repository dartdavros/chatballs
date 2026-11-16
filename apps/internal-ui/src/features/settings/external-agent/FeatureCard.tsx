import { SwitchButton } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { ServiceAlert } from "../../integrations/services/connect/ServiceAlert";
import { et } from "./copy";
import { HelpTitle } from "./HelpTitle";

export function FeatureCard({ enabled, retained, review, busy, failed, onToggle }: {
  enabled: boolean; retained: boolean; review: boolean; busy: boolean; failed: "enable" | "save" | null; onToggle: () => void;
}) {
  if (retained) return <section className="administration-card ea-external-feature" data-external-feature={!enabled ? "off-retained" : review ? "review-required" : "on"}>
    <div className="settings-card-head"><div><HelpTitle title={et("settings.feature")} topic="external" />
      <small>{et("settings.featureLead")}</small></div>
      <SwitchButton checked={enabled} disabled={busy} className="ui-switch" label={et("settings.feature")} onClick={onToggle} />
    </div>
    <div className="external-feature-state">
      <p className="settings-section-note">{et(enabled ? "settings.featureOn" : "settings.featureOff")}</p>
      {failed && <div role="alert"><ServiceAlert tone="error" title={et(failed === "enable" ? "feedback.enableErrorTitle" : "feedback.saveErrorTitle")}
        text={et(failed === "enable" ? "feedback.enableErrorHelp" : "feedback.saveErrorHelp")} /></div>}
      {(!enabled || review) && <><div className="settings-risk-note"><Icon name="warning" size={16} />
        <p>{et(enabled ? "settings.reviewLead" : "settings.disabledLead")}</p></div>
        <StatusPill status={enabled ? "pending" : "archived"} label={et(enabled ? "policy.needsReview" : "settings.retained")} /></>}
    </div>
  </section>;
  return <section className="administration-card" data-external-feature={enabled ? "on" : "off"}>
    <div className="settings-card-head"><div><strong>{et("off.externalTitle")}</strong>
      <small>{et("off.externalDescription")}</small></div>
      <span className="settings-card-head-switch"><SwitchButton checked={enabled} disabled={busy} className="ui-switch" label={et("off.externalTitle")} onClick={onToggle} /></span>
    </div>
    <p className="settings-section-note">{et(enabled ? "setup.externalHelp" : "off.externalHelp")}</p>
    <p className="settings-section-note">{et("off.externalPreserved")}</p>
    {failed && <div className="external-feature-state">
      <ServiceAlert tone="error" title={et(failed === "enable" ? "feedback.enableErrorTitle" : "feedback.saveErrorTitle")}
        text={et(failed === "enable" ? "feedback.enableErrorHelp" : "feedback.saveErrorHelp")} />
    </div>}
  </section>;
}
