import { FormField, SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { LogoSpinner } from '../../../../../apps/internal-ui/src/shared/icons';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { StatusPill } from '../../../../../apps/internal-ui/src/shared/ui';
import { ServiceAlert } from '../../../../../apps/internal-ui/src/features/integrations/services/connect/ServiceAlert';
import { HelpTrigger } from '../shared/HelpTrigger';
import { tx, type CopyKey } from './copy';
import './key-actions.css';

const failures: Record<string, [CopyKey, CopyKey]> = {
  S28: ['accessError', 'accessHelp'], S29: ['unavailable', 'unavailableHelp'], S30: ['incompatible', 'incompatibleHelp'],
};
export function ConnectionCard({ variant, width }: { variant: string; width: number }) {
  const checking = variant === 'S27', off = ['S38', 'S72'].includes(variant), disabled = off || variant === 'S34', review = variant === 'S39';
  const connectionDisabled = variant === 'S73';
  const failure = failures[variant];
  return <section className="administration-card" data-connection-active={connectionDisabled ? 'false' : 'true'} data-connection-check={connectionDisabled ? 'disabled' : checking ? 'pending' : failure ? 'failed' : review ? 'review-required' : off ? 'retained' : 'ready'}>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('connection')}</strong><HelpTrigger topic="keys" /></span></div>
      <StatusPill status={connectionDisabled || off ? 'archived' : checking || review ? 'pending' : failure ? 'error' : 'healthy'}
        label={tx(connectionDisabled ? 'connectionDisabled' : checking ? 'statusChecking' : failure ? 'statusError' : review ? 'statusReview' : off ? 'statusRetained' : 'statusReady')} />
    </div>
    {connectionDisabled && <div className="service-connection-access" data-connection-disabled>
      <div><strong>{tx('connectionActive')}</strong></div>
      <SwitchButton className="ui-switch" checked={false} label={tx('connectionActive')} onClick={() => {}} />
    </div>}
    <div className="administration-fields">
      <FormField label={tx('name')} value={tx('nameValue')} disabled={disabled} onChange={() => {}} />
      <FormField label={tx('address')} value={tx('addressValue')} disabled={disabled} onChange={() => {}} mono />
      <div className="service-connect-stack ea-key-field" data-saved-secret="outgoing"><FormField label={tx('outgoing')} value="" type="password" placeholder="••••••••••••" disabled />
        <small className="settings-section-note">{tx('stored')}</small>
        <div className="ea-key-actions"><Button variant="secondary" icon="refresh" disabled={disabled || checking} onClick={() => {}}>{tx('replace')}</Button></div></div>
      <div className="service-connect-stack ea-key-field" data-saved-secret="incoming"><FormField label={tx('incoming')} value="" type="password" placeholder="••••••••••••" disabled />
        <small className="settings-section-note">{tx('stored')}</small>
        <div className="ea-key-actions">
          <Button variant="secondary" icon="refresh" disabled={disabled || checking} onClick={() => {}}>{tx('replace')}</Button>
          <Button variant="danger-outline" icon="xCircle" disabled={disabled || checking} onClick={() => {}}>{tx('revoke')}</Button>
        </div></div>
    </div>
    <div className="administration-actions">
      <Button variant="secondary" disabled={disabled || checking || connectionDisabled} onClick={() => {}}>{tx(checking ? 'checking' : 'check')}</Button>
    </div>
    <div className="service-connection-access" style={{ minHeight: width <= 900 ? 224 : 112 }} data-capability-result>
      {checking ? <div className="service-oauth-waiting" role="status" aria-label={tx('checking')}>
        <span aria-hidden="true"><LogoSpinner size={18} /></span><div><strong>{tx('checking')}</strong><span>{tx('checkHelp')}</span></div>
      </div> : failure ? <ServiceAlert tone="error" title={tx(failure[0])} text={tx(failure[1])} />
        : connectionDisabled ? <ServiceAlert tone="error" title={tx('connectionDisabled')} text={tx('connectionDisabledLead')} />
        : <div><span className="external-help-title"><strong>{tx('capability')}</strong><HelpTrigger topic="capability" /></span><p>{tx(review ? 'reviewLead' : off ? 'disabledLead' : 'capabilityReady')}</p><p>{tx('formats')}</p></div>}
    </div>
  </section>;
}
