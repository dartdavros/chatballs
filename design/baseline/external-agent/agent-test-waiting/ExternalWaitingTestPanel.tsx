import { useEffect, useId, useRef } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import '../../../../apps/internal-ui/src/features/agents/test-chat/styles.css';
import '../../../../apps/internal-ui/src/features/agents/actions/actions.css';
import { PendingTestFeed } from './PendingTestFeed';
import { WaitingTestClientData } from './WaitingTestClientData';
import { tx } from './copy';

// One static waiting frame; no API, timing, receipt, cancellation or response is simulated.
export function ExternalWaitingTestPanel({ onClose }: { onClose: () => void }) {
  const titleId = useId();
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => opener?.focus();
  }, []);
  return <aside className="agent-test-panel" data-test-state="waiting" ref={panel} tabIndex={-1}
    role="dialog" aria-labelledby={titleId}
    onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); onClose(); } }}>
    <header className="agent-test-head">
      <div><strong id={titleId}>{t('agent_test.title')}</strong><small>{tx('panelSubtitle')}</small></div>
      <button type="button" title={t('agent_test.restart')} aria-label={t('agent_test.restart')} disabled>
        <Icon name="refresh" size={15} strokeWidth={2.2} />
      </button>
      <button type="button" title={t('common.close')} aria-label={t('common.close')} onClick={onClose}>
        <Icon name="close" size={15} strokeWidth={2.4} />
      </button>
    </header>
    <div className="agent-action-test-mode is-warning" data-external-test>
      <strong>{tx('externalMode')}</strong><p>{tx('externalTestWarning')}</p>
    </div>
    <WaitingTestClientData />
    <PendingTestFeed message={tx('messageText')} />
    <form className="agent-test-composer" onSubmit={event => event.preventDefault()}>
      <div><input value="" aria-label={t('agent_test.placeholder')} placeholder={t('agent_test.placeholder')}
        disabled readOnly maxLength={10000} />
        <button type="submit" disabled aria-busy="true">{t('conversations.send')}</button>
      </div>
    </form>
  </aside>;
}
