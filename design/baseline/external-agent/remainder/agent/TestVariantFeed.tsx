import { TestChatFeed } from '../../../../../apps/internal-ui/src/features/agents/test-chat/TestChatFeed';
import { LogoSpinner } from '../../../../../apps/internal-ui/src/shared/icons';
import '../../../../../apps/internal-ui/src/features/integrations/services/services.css';
import '../../agent-test-waiting/waiting.css';
import { agent } from './data';
import { tx } from './copy';
import { HelpTrigger } from '../shared/HelpTrigger';

export function TestVariantFeed({ variant }: { variant: string }) {
  const turn = { message: tx('question'), calls: [], createdAt: '2026-11-15T09:00:00Z' };
  if (variant === 'S07') return <TestChatFeed agentName={agent.name} turns={[{...turn, reply:tx('reply')}]} />;
  if (variant === 'S09') return <TestChatFeed agentName={agent.name} turns={[{...turn, error:tx('error')}]} />;
  if (variant === 'S11') return <TestChatFeed agentName={agent.name} turns={[]} />;
  const waiting = variant === 'S08';
  return <div className="agent-test-feed" role="log" aria-live="polite">
    <div className="agent-test-client"><div>{turn.message}</div></div>
    <div className="service-oauth-waiting" data-external-waiting role="status">
      {waiting && <span aria-hidden="true"><LogoSpinner size={18} /></span>}
      <div><span className="external-help-title"><strong>{tx(waiting ? 'longWait' : 'interrupted')}</strong>{waiting && <HelpTrigger topic="processing" />}</span>
        <span>{tx(waiting ? 'longHelp' : 'interruptedHelp')}</span></div>
    </div>
  </div>;
}
