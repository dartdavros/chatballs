import { useEffect, useId, useRef } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import { TestChatFeed } from '../../../../apps/internal-ui/src/features/agents/test-chat/TestChatFeed';
import '../../../../apps/internal-ui/src/features/agents/test-chat/styles.css';
import '../../../../apps/internal-ui/src/features/agents/actions/actions.css';
import { ExternalTestClientData } from './ExternalTestClientData';
import { tx } from './copy';

// Static initial panel. No data hook, service request, draft state or synthetic response.
export function ExternalAgentTestPanel({ agentName, onClose }: { agentName: string; onClose: () => void }) {
  const titleId = useId();
  const panel = useRef<HTMLElement>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => opener?.focus();
  }, []);
  return <aside className="agent-test-panel" ref={panel} tabIndex={-1} role="dialog" aria-labelledby={titleId}
    onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); onClose(); } }}>
    <header className="agent-test-head">
      <div><strong id={titleId}>{t('agent_test.title')}</strong><small>{tx('panelSubtitle')}</small></div>
      <button type="button" title={t('agent_test.restart')} aria-label={t('agent_test.restart')}
        onClick={() => input.current?.focus()}><Icon name="refresh" size={15} strokeWidth={2.2} /></button>
      <button type="button" title={t('common.close')} aria-label={t('common.close')} onClick={onClose}>
        <Icon name="close" size={15} strokeWidth={2.4} />
      </button>
    </header>
    <div className="agent-action-test-mode is-warning" data-external-test>
      <strong>{tx('externalMode')}</strong>
      <p>{tx('externalTestWarning')}</p>
    </div>
    <ExternalTestClientData />
    <TestChatFeed turns={[]} agentName={agentName} />
    <form className="agent-test-composer" onSubmit={event => event.preventDefault()}>
      <div><input ref={input} value="" aria-label={t('agent_test.placeholder')} placeholder={t('agent_test.placeholder')}
        onChange={() => {}} maxLength={10000} />
        <button type="submit" disabled aria-busy={false}>{t('conversations.send')}</button>
      </div>
    </form>
  </aside>;
}
