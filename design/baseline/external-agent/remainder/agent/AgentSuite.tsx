import { t } from '../../../../../apps/internal-ui/src/i18n';
import { BackLink } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { AgentHeader } from '../../../../../apps/internal-ui/src/features/agents/AgentHeader';
import { AssignmentCard } from '../../../../../apps/internal-ui/src/features/agents/AssignmentCard';
import { ConnectionsCard } from '../../../../../apps/internal-ui/src/features/agents/ConnectionsCard';
import { AgentWorkbenchSidebar } from '../../agent-external/AgentWorkbenchSidebar';
import { ResponseLanguageCard } from '../../agent-external/ResponseLanguageCard';
import { SpeechCard } from '../../agent-external/SpeechCard';
import { ExecutionState, blocked } from './ExecutionState';
import { BuiltinMain, BuiltinActions, BuiltinTools } from './BuiltinViews';
import { TestVariantPanel } from './TestVariantPanel';
import { GuardedAgentHeader } from './GuardedAgentHeader';
import { AssistanceView } from './AssistanceView';
import { agent, builtIn, withoutLlm, groups, noop, unchanged } from './data';

export function AgentSuite({variant,width,height}:{variant:string;width:number;height:number}) {
  const testing = ['S07','S08','S09','S10','S11'].includes(variant);
  const builtin = variant === 'S12' || variant === 'S13';
  const card = builtin ? builtIn : variant === 'S70' ? withoutLlm : agent;
  return <div className={`ea-screen ${blocked(variant)?'ea-agent-blocked':''}`} data-screen={variant} style={{width,height}}
    onClickCapture={event=>{const element=event.target as Element;if(element.closest('a,.work-status-trigger,.agent-assistance-toggle,.agent-inline-button') || element.closest('button')?.textContent?.trim()===t('ai.copy_snippet')){event.preventDefault();event.stopPropagation();}}}>
    <div className="hub-shell"><AgentWorkbenchSidebar /><div className="hub-main"><main className="hub-scroll agents-scroll">
      <div className="hub-page agents-page-shell"><div className="agent-page">
        <BackLink label={t('common.agents')} onClick={noop} />
        {blocked(variant) ? <GuardedAgentHeader card={card}/> : <AgentHeader card={card} canManage busy={false} testing={testing} apply={unchanged}
          toggleAi={async()=>{}} onDelete={noop} onTest={noop} />}
        <div className="agent-grid"><div className="agent-column">
          <ExecutionState variant={variant} />
          {builtin ? <BuiltinMain /> : <><ResponseLanguageCard /><SpeechCard /></>}
        </div><div className="agent-column">
          {builtin && <BuiltinActions />}
          <AssignmentCard card={card} groups={groups} canManage busy={false} apply={unchanged} />
          <AssistanceView card={card} />
          <ConnectionsCard card={card} canManage busy={false} available={[]} openChannels={noop} bind={noop} unbind={noop} />
          {builtin && <BuiltinTools />}
        </div></div>
        {testing && <TestVariantPanel variant={variant} />}
      </div></div>
    </main></div></div>
  </div>;
}
