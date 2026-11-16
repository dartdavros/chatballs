import { useId } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import { tx } from './copy';

// Accepted empty-policy presentation; its heading is unavailable during the pending request.
export function WaitingTestClientData() {
  const id = useId();
  return <section className="agent-test-data" data-external-test-data="empty">
    <button type="button" className="agent-test-data-heading" disabled aria-expanded="true" aria-controls={`${id}-fields`}>
      <Icon name="user" size={15} strokeWidth={1.9} />
      <span><strong>{t('agent_test.client_data')}</strong></span>
      <span className="is-expanded"><Icon name="chevron" size={14} strokeWidth={2.2} /></span>
    </button>
    <div id={`${id}-fields`} className="agent-test-fields">
      <small className="agent-test-data-hint">{tx('testDataEmpty')}</small>
    </div>
  </section>;
}
