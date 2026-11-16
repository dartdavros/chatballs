import { HelpTitle } from "./HelpTitle";
import { LogoSpinner } from "../../../shared/icons";
import { ServiceAlert } from "../../integrations/services/connect/ServiceAlert";
import { et } from "./copy";

const failureKeys = { access: ["settings.accessError", "settings.accessHelp"], unavailable: ["settings.unavailable", "settings.unavailableHelp"],
  incompatible: ["settings.incompatible", "settings.incompatibleHelp"] } as const;
export function CapabilitiesResult({ checking, failed, failure, compatible, enabled, retained, review, disabledHelp }: {
  checking: boolean; failed: boolean; failure: keyof typeof failureKeys; compatible: boolean; enabled: boolean; retained: boolean; review: boolean;
  disabledHelp: string;
}) {
  const error = failureKeys[failure];
  return <div className="service-connection-access external-capability-result" data-capability-result>
    {checking ? <div className="service-oauth-waiting" role="status"><span aria-hidden="true"><LogoSpinner size={18} /></span><div><strong>{et("settings.checking")}</strong><span>{et("settings.checkHelp")}</span></div></div>
      : failed ? <ServiceAlert tone="error" title={et(error[0])} text={et(error[1])} />
      : !enabled ? <ServiceAlert tone="error" title={et("settings.connectionDisabled")} text={disabledHelp} />
      : <div><HelpTitle title={et("settings.capability")} topic="capability" /><p>{et(review ? "settings.reviewLead" : retained ? "settings.disabledLead" : compatible ? "settings.capabilityReady" : "agent.notReady")}</p>
        {(compatible || retained || review) && <p>{et("settings.formats")}</p>}</div>}
  </div>;
}
