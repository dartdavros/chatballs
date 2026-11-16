import { FormField, SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { tx } from './copy';
import { HelpTrigger } from '../shared/HelpTrigger';

// Values are an illustrative saved configuration, not newly defined API defaults.
export function ProcessingCard({ disabled = false }: { disabled?: boolean }) {
  return <section className="administration-card" data-processing-settings>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('processing')}</strong><HelpTrigger topic="processing" /></span><small>{tx('processingHelp')}</small></div></div>
    <div className="administration-fields">
      <FormField label={tx('ordinary')} value="120" type="number" disabled={disabled} onChange={() => {}} />
      <FormField label={tx('long')} value="7200" type="number" disabled={disabled} onChange={() => {}} />
      <FormField label={tx('maximum')} value="86400" type="number" disabled={disabled} onChange={() => {}} />
    </div>
    <p className="settings-section-note">{tx('illustrativeTiming')}</p><p className="settings-section-note">{tx('timeoutHelp')}</p>
    <div className="service-connection-access" data-initiative-agent="support" data-initiative-connection="support-service"><div><span className="external-help-title"><strong>{tx('initiative')}</strong><HelpTrigger topic="initiative" /></span><p>{tx('initiativeHelp')}</p></div>
      <SwitchButton className="ui-switch" checked={false} label={`${tx('initiative')}: ${tx('supportAgent')} · ${tx('nameValue')}`} disabled={disabled} onClick={() => {}} />
    </div>
  </section>;
}
