import type { MouseEvent } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { BackLink } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { AgentHeader } from '../../../../apps/internal-ui/src/features/agents/AgentHeader';
import { AssignmentCard } from '../../../../apps/internal-ui/src/features/agents/AssignmentCard';
import { ConnectionsCard } from '../../../../apps/internal-ui/src/features/agents/ConnectionsCard';
import { AgentWorkbenchSidebar } from './AgentWorkbenchSidebar';
import { ExecutionCard } from './ExecutionCard';
import { ResponseLanguageCard } from './ResponseLanguageCard';
import { SpeechCard } from './SpeechCard';
import { IndependentAssistanceCard } from './IndependentAssistanceCard';
import { agent, groups, noop, unchanged } from './design-data';

function keepContextStatic(event: MouseEvent<HTMLDivElement>) {
  const target = event.target as Element;
  const button = target.closest('button');
  if (target.closest('a, .work-status-trigger, .agent-assistance-toggle')
      || button?.textContent?.trim() === t('ai.copy_snippet')) {
    event.preventDefault(); event.stopPropagation();
  }
}

export function AgentScreen({ width, height }: { width: number; height: number }) {
  return <div className="ea-screen" data-screen="S04" style={{ width, height }} onClickCapture={keepContextStatic}>
    <div className="hub-shell">
      <AgentWorkbenchSidebar />
      <div className="hub-main"><main className="hub-scroll agents-scroll"><div className="hub-page agents-page-shell">
        <div className="agent-page">
          <BackLink label={t('common.agents')} onClick={noop} />
          <AgentHeader card={agent} canManage busy={false} testing={false} apply={unchanged}
            toggleAi={async () => {}} onDelete={noop} onTest={noop} />
          <div className="agent-grid">
            <div className="agent-column"><ExecutionCard /><ResponseLanguageCard /><SpeechCard /></div>
            <div className="agent-column">
              <AssignmentCard card={agent} groups={groups} canManage busy={false} apply={unchanged} />
              <IndependentAssistanceCard />
              <ConnectionsCard card={agent} canManage busy={false} available={[]} openChannels={noop} bind={noop} unbind={noop} />
            </div>
          </div>
        </div>
      </div></main></div>
    </div>
  </div>;
}
