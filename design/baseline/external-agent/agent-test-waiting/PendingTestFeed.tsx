import { LogoSpinner } from '../../../../apps/internal-ui/src/shared/icons';
import '../../../../apps/internal-ui/src/features/integrations/services/services.css';
import { tx } from './copy';
import './waiting.css';

// Current TestChatFeed bubble and log; the source component has no waiting-status slot.
export function PendingTestFeed({ message }: { message: string }) {
  return <div className="agent-test-feed" role="log" aria-live="polite">
    <div><div className="agent-test-client"><div>{message}</div></div></div>
    <div className="service-oauth-waiting" data-external-waiting role="status" aria-label={tx('waitingLabel')}>
      <span aria-hidden="true"><LogoSpinner size={18} /></span>
      <div><strong>{tx('waitingLabel')}</strong><span>{tx('waitingHelp')}</span></div>
    </div>
  </div>;
}
