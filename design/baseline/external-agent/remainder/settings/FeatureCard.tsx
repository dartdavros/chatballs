import { SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { StatusPill } from '../../../../../apps/internal-ui/src/shared/ui';
import { HelpTrigger } from '../shared/HelpTrigger';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { ServiceAlert } from '../../../../../apps/internal-ui/src/features/integrations/services/connect/ServiceAlert';
import { tx } from './copy';
import './key-actions.css';

export function FeatureCard({ variant }: { variant: string }) {
  const off = ['S38', 'S72'].includes(variant), review = variant === 'S39', busy = variant === 'S34';
  return <section className="administration-card ea-external-feature" data-external-feature={off ? 'off-retained' : review ? 'review-required' : 'on'}>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('feature')}</strong><HelpTrigger topic="external" /></span><small>{tx('featureLead')}</small></div>
      <SwitchButton className="ui-switch" checked={!off} disabled={busy} label={tx('feature')} onClick={() => {}} />
    </div>
    <div className="external-feature-state">
      <p className="settings-section-note">{tx(off ? 'featureOff' : 'featureOn')}</p>
      {variant === 'S72' && <div role="alert" data-feature-enable-error><ServiceAlert tone="error" title={tx('enableErrorTitle')} text={tx('enableErrorHelp')} /></div>}
      {(off || review) && <div className="settings-risk-note"><Icon name="warning" size={16} /><p>{tx(off ? 'disabledLead' : 'reviewLead')}</p></div>}
      {(off || review) && <StatusPill status={off ? 'archived' : 'pending'} label={tx(off ? 'retained' : 'needsReview')} />}
    </div>
  </section>;
}
