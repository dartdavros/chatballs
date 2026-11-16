import type { MouseEvent } from 'react';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { BackLink } from '../../../../apps/internal-ui/src/shared/ui-controls';
import { AgentHeader } from '../../../../apps/internal-ui/src/features/agents/AgentHeader';
import { AssignmentCard } from '../../../../apps/internal-ui/src/features/agents/AssignmentCard';
import { ConnectionsCard } from '../../../../apps/internal-ui/src/features/agents/ConnectionsCard';
import { AgentWorkbenchSidebar } from '../agent-external/AgentWorkbenchSidebar';
import { ExecutionCard } from '../agent-external/ExecutionCard';
import { ResponseLanguageCard } from '../agent-external/ResponseLanguageCard';
import { SpeechCard } from '../agent-external/SpeechCard';
import { IndependentAssistanceCard } from '../agent-external/IndependentAssistanceCard';
import { agent, groups, noop, unchanged } from '../agent-external/design-data';
import { ExternalAgentTestPanel } from './ExternalAgentTestPanel';

function keepContextStatic(event: MouseEvent<HTMLDivElement>) {
  const target = event.target as Element;
  if (target.closest('a, .work-status-trigger, .agent-assistance-toggle')
      || target.closest('button')?.textContent?.trim() === t('ai.copy_snippet')) {
    event.preventDefault(); event.stopPropagation();
  }
}

// Current page composition with the approved external subviews and the test panel open.
export function AgentTestScreen({ width, height }: { width: number; height: number }) {
  return <div className="ea-screen" data-screen="S05" style={{ width, height }} onClickCapture={keepContextStatic}>
    <div className="hub-shell">
      <AgentWorkbenchSidebar />
      <div className="hub-main"><main className="hub-scroll agents-scroll"><div className="hub-page agents-page-shell">
        <div className="agent-page">
          <BackLink label={t('common.agents')} onClick={noop} />
          <AgentHeader card={agent} canManage busy={false} testing apply={unchanged}
            toggleAi={async () => {}} onDelete={noop} onTest={noop} />
          <div className="agent-grid">
            <div className="agent-column"><ExecutionCard /><ResponseLanguageCard /><SpeechCard /></div>
            <div className="agent-column">
              <AssignmentCard card={agent} groups={groups} canManage busy={false} apply={unchanged} />
              <IndependentAssistanceCard />
              <ConnectionsCard card={agent} canManage busy={false} available={[]} openChannels={noop} bind={noop} unbind={noop} />
            </div>
          </div>
          <ExternalAgentTestPanel agentName={agent.name} onClose={noop} />
        </div>
      </div></main>
      </div>
    </div>
  </div>;
}
