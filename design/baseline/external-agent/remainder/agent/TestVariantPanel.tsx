import { useEffect, useId, useRef } from 'react';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import '../../../../../apps/internal-ui/src/features/agents/test-chat/styles.css';
import '../../../../../apps/internal-ui/src/features/agents/actions/actions.css';
import { ExternalTestClientData } from '../../agent-test/ExternalTestClientData';
import { WaitingTestClientData } from '../../agent-test-waiting/WaitingTestClientData';
import { TestClientFields } from './TestClientFields';
import { TestVariantFeed } from './TestVariantFeed';
import { tx } from './copy';
import { noop } from './data';

export function TestVariantPanel({variant}:{variant:string}) {
  const id = useId(), waiting = variant === 'S08', interrupted = variant === 'S10';
  const panel=useRef<HTMLElement>(null);
  useEffect(()=>{const opener=document.activeElement as HTMLElement|null;panel.current?.focus();return()=>opener?.focus();},[]);
  return <aside className="agent-test-panel" ref={panel} role="dialog" aria-labelledby={id} tabIndex={-1} data-test-state={variant}
    onKeyDown={event => { if(event.key === 'Escape') event.stopPropagation(); }}>
    <header className="agent-test-head"><div><strong id={id}>{t('agent_test.title')}</strong><small>{tx('testSubtitle')}</small></div>
      <button type="button" disabled={waiting} title={t('agent_test.restart')} aria-label={t('agent_test.restart')} onClick={noop}><Icon name="refresh" size={15} /></button>
      <button type="button" title={t('common.close')} aria-label={t('common.close')} onClick={noop}><Icon name="close" size={15} /></button>
    </header>
    <div className="agent-action-test-mode is-warning" data-external-test><strong>{tx('real')}</strong><p>{tx('warning')}</p></div>
    {variant === 'S11' ? <TestClientFields /> : waiting ? <WaitingTestClientData /> : <ExternalTestClientData />}
    <TestVariantFeed variant={variant} />
    <form className="agent-test-composer" onSubmit={event=>event.preventDefault()}><div>
      <input value="" onChange={noop} disabled={waiting || interrupted} aria-label={t('agent_test.placeholder')}
        placeholder={t('agent_test.placeholder')} maxLength={10000} />
      <button type="submit" disabled aria-busy={waiting}>{t('conversations.send')}</button>
    </div></form>
  </aside>;
}
