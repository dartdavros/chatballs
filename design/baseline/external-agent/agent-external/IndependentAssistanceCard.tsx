import { t } from '../../../../apps/internal-ui/src/i18n';
import { SwitchButton } from '../../../../apps/internal-ui/src/shared/form-controls';
import '../../../../apps/internal-ui/src/features/agents/assistance.css';
import { agent, noop } from './design-data';
import { tx } from './copy';

// Current AssistanceCard presentation; neutral AI-button caption proposed for the stopped state.
// The design has no persistence hook and does not simulate saving.
export function IndependentAssistanceCard() {
  const aiActive = agent.aiStatus === 'ACTIVE';
  return <section className="agent-card is-side agent-assistance" aria-busy={false}>
    <h3>{t('agent_assistance.title')}<i title={t('agent_assistance.new_block')} /></h3>
    <p>{t('agent_assistance.description')}</p>
    <div className="agent-assistance-toggle">
      <div><strong>{t('agent_assistance.drafts')}</strong>
        <small>{t(aiActive ? 'agent_assistance.independent' : 'agent_assistance.ai_stopped')}</small></div>
      <SwitchButton className="ui-switch is-compact" label={t('agent_assistance.drafts')}
        checked={agent.assistanceEnabled} onClick={noop} />
    </div>
    <div className="agent-assistance-toggle">
      <div><strong>{t('agent_assistance.autonomous')}</strong><small>{tx('autonomousHelp')}</small></div>
      <SwitchButton className="ui-switch is-compact is-comparison" label={t('agent_assistance.autonomous')}
        checked={aiActive} disabled onClick={noop} />
    </div>
    <div className="agent-assistance-footer" role="status">
      <small>{t(agent.assistanceEnabled ? 'agent_assistance.enabled' : 'agent_assistance.disabled')}</small>
    </div>
  </section>;
}
