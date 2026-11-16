import { SelectField } from '../../../../apps/internal-ui/src/shared/form-controls';
import { StatusPill } from '../../../../apps/internal-ui/src/shared/ui';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import { noop } from './design-data';
import { tx } from './copy';

export function ExecutionCard() {
  return <section className="agent-card" data-execution-mode="external">
    <div className="agent-card-head"><h3>{tx('executionTitle')}</h3></div>
    <p className="settings-section-note">{tx('paused')}</p>
    <div className="agent-side-fields">
      <SelectField label={tx('executionMethod')} value="external" onChange={noop}
        options={[[ 'builtin', tx('builtin') ], [ 'external', tx('external') ]]} />
      <div data-executor-name><SelectField label={tx('executor')} value="support" onChange={noop}
        options={[[ 'support', tx('executorName') ]]} /></div>
      <div className="agent-card-head is-tight">
        <StatusPill status="healthy" label={tx('connectionReady')} />
        <button type="button" className="link has-icon" onClick={noop}>{tx('settings')}<Icon name="external" size={13} /></button>
      </div>
      <small className="settings-section-note" data-builtin-preserved>{tx('builtinPreserved')}</small>
    </div>
  </section>;
}
