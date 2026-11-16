import { SelectField } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { StatusPill } from '../../../../../apps/internal-ui/src/shared/ui';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { noop } from './data';
import { tx } from './copy';
import { HelpTrigger } from '../shared/HelpTrigger';

const reasons = { S14: 'notReady', S15: 'disabled', S16: 'unavailable', S17: 'incompatible',
  S18: 'permission', S19: 'consent', S71: 'connectionDisabled' } as const;
export const blocked = (variant: string) => variant !== 'S19' && Object.hasOwn(reasons, variant);
export function ExecutionState({ variant }: { variant: string }) {
  if (variant === 'S12') return null;
  const builtin = variant === 'S13';
  const key = reasons[variant as keyof typeof reasons];
  return <section className="agent-card" data-execution-mode={builtin ? 'builtin' : 'external'}>
    <div className="agent-card-head"><span className="external-help-title"><h3>{tx('executionTitle')}</h3><HelpTrigger topic="external" /></span></div>
    {!key && <p className="settings-section-note">{tx(builtin ? 'returned' : 'paused')}</p>}
    <div className="agent-side-fields">
      <SelectField label={tx('method')} value={builtin ? 'builtin' : 'external'} onChange={noop}
        options={[[ 'builtin', tx('builtin') ], [ 'external', tx('external') ]]} disabled={variant === 'S15'} />
      {!builtin && <SelectField label={tx('executor')} value={variant === 'S14' ? '' : 'support'} onChange={noop}
        disabled={variant === 'S15'} options={variant === 'S14' ? [['', '—']] : [['support', tx('service')]]} />}
      {key && <div className="agent-feedback is-warning" role="alert">{tx(key)}</div>}
      <div className="agent-card-head is-tight">
        <StatusPill status={key && variant !== 'S19' ? 'disabled' : 'healthy'} label={key && variant !== 'S19' ? tx('unavailableLabel') : builtin ? tx('builtin') : tx('ready')} />
        <button className="link has-icon" type="button" onClick={noop}>{tx('settings')}<Icon name="external" size={13} /></button>
      </div>
      {!builtin && <small className="settings-section-note">{tx(variant === 'S70' ? 'missingLlm' : 'preserved')}</small>}
    </div>
  </section>;
}
