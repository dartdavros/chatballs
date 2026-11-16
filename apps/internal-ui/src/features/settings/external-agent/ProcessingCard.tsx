import { HelpTitle } from "./HelpTitle";
import { fmt } from "../../../i18n";
import { FormField, SelectField, SwitchButton } from "../../../shared/form-controls";
import { et } from "./copy";
import type { ExternalBinding } from "./model";

const duration = (seconds: number) => fmt.number(seconds % 3600 === 0 ? seconds / 3600 : seconds % 60 === 0 ? seconds / 60 : seconds,
  { style: "unit", unit: seconds % 3600 === 0 ? "hour" : seconds % 60 === 0 ? "minute" : "second", unitDisplay: "long" });
export function ProcessingCard({ binding, connection, disabled, change }: {
  binding: ExternalBinding; connection: string; disabled: boolean; change: (patch: Partial<ExternalBinding>) => void;
}) {
  return <section className="administration-card" data-processing-settings>
    <div className="settings-card-head"><div><HelpTitle title={et("settings.processing")} topic="processing" /><small>{et("settings.processingHelp")}</small></div></div>
    <div className="administration-fields"><SelectField label={et("settings.processingMode")} value={binding.processingMode}
      disabled={disabled} options={[["ordinary", et("settings.ordinaryMode")], ["long", et("settings.longMode")]]}
      onChange={value => change({ processingMode: value as ExternalBinding["processingMode"] })} />
      {(["ordinary", "long", "maximum"] as const).map(key => <FormField key={key}
      label={et(`settings.${key}`)} value={String(binding[`${key}Timeout`])} type="number" disabled={disabled}
      onChange={value => change({ [`${key}Timeout`]: value === "" ? 0 : Number(value) })} />)}</div>
    <p className="settings-section-note">{et("settings.illustrativeTiming", { ordinary: duration(binding.ordinaryTimeout), long: duration(binding.longTimeout), maximum: duration(binding.maximumTimeout) })}</p>
    <p className="settings-section-note">{et("settings.timeoutHelp")}</p>
    <div className="service-connection-access"><div><HelpTitle title={et("settings.initiative")} topic="initiative" />
      <p>{et(binding.proactiveEnabled ? "settings.initiativeActiveHelp" : "settings.initiativeHelp", { agent: binding.agentName, connection })}</p></div>
      <SwitchButton className="ui-switch" checked={binding.proactiveEnabled} disabled={disabled} label={et("settings.initiative")}
        onClick={() => change({ proactiveEnabled: !binding.proactiveEnabled })} />
    </div>
  </section>;
}
