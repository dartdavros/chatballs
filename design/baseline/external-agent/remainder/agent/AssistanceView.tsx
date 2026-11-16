import { t } from '../../../../../apps/internal-ui/src/i18n';
import { SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import type { AgentCard } from '../../../../../apps/internal-ui/src/features/agents/model';
import '../../../../../apps/internal-ui/src/features/agents/assistance.css';
import { noop } from './data';
import { tx } from './copy';

export function AssistanceView({card}:{card:AgentCard}) {
  return <section className="agent-card is-side agent-assistance" aria-busy={false}>
    <h3>{t('agent_assistance.title')}<i title={t('agent_assistance.new_block')}/></h3><p>{t('agent_assistance.description')}</p>
    <div className="agent-assistance-toggle"><div><strong>{t('agent_assistance.drafts')}</strong><small>{t('agent_assistance.ai_stopped')}</small></div>
      <SwitchButton className="ui-switch is-compact" label={t('agent_assistance.drafts')} checked={card.assistanceEnabled} onClick={noop}/></div>
    <div className="agent-assistance-toggle"><div><strong>{t('agent_assistance.autonomous')}</strong><small>{tx('assistanceHelp')}</small></div>
      <SwitchButton className="ui-switch is-compact is-comparison" label={t('agent_assistance.autonomous')} checked={false} disabled onClick={noop}/></div>
    <div className="agent-assistance-footer" role="status"><small>{t(card.assistanceEnabled?'agent_assistance.enabled':'agent_assistance.disabled')}</small></div>
    {card.providerIntegrationId===null&&<div className="agent-assistance-note is-warning"><Icon name="warning" size={14}/><span>{tx('assistanceMissing')}</span></div>}
  </section>;
}
