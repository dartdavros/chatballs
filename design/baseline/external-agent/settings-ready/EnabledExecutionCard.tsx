import { SwitchButton } from '../../../../apps/internal-ui/src/shared/form-controls';
import { tx } from './copy';

export function EnabledExecutionCard() {
  return <section className="administration-card" data-external-card aria-labelledby="external-execution-title">
    <div className="settings-card-head">
      <div><strong id="external-execution-title">{tx('externalTitle')}</strong><small>{tx('externalDescription')}</small></div>
      <span className="settings-card-head-switch" data-external-toggle>
        <SwitchButton checked className="ui-switch" label={tx('externalTitle')} onClick={() => {}} />
      </span>
    </div>
    <p className="settings-section-note">{tx('externalHelp')}</p>
    <p className="settings-section-note">{tx('externalPreserved')}</p>
  </section>;
}
