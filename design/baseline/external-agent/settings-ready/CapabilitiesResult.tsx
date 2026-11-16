import { Button } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill } from '../../../../apps/internal-ui/src/shared/ui';
import { tx } from './copy';

// Reuses SpeechSettingsContent's allocated capability-check row, without its service hook.
export function CapabilitiesResult() {
  return <div className="service-connect-fields">
    <div className="speech-check">
      <strong>{tx('checkTitle')}</strong>
      <div role="status" className="speech-check-status" data-capabilities-result>
        <StatusPill status="healthy" label={tx('compatibility')} />
      </div>
      <Button variant="secondary" onClick={() => {}}>{tx('checkConnection')}</Button>
    </div>
    <p className="service-connect-note">{tx('capabilitiesSummary')}</p>
    <p className="service-connect-note">{tx('formats')} {tx('channelLimits')}</p>
    <p className="service-connect-note">{tx('checkHint')}</p>
  </div>;
}
