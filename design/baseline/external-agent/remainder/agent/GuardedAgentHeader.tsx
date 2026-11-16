import { Dropdown } from 'antd';
import { t } from '../../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { groupColorOf } from '../../../../../apps/internal-ui/src/features/conversations/model';
import { agentTile, agentStatusMeta, createdLabel, openDialogsLine, type AgentCard } from '../../../../../apps/internal-ui/src/features/agents/model';
import { noop } from './data';

// Current AgentHeader presentation, with semantic disabled test/start controls for unavailable execution.
export function GuardedAgentHeader({card}:{card:AgentCard}) {
  const tile=agentTile(card), status=agentStatusMeta(card);
  const items=[
    {key:'copy',label:<button type="button" onClick={noop}><Icon name="copy" size={15}/>{t('ai.copy_snippet')}</button>},
    {type:'divider' as const},
    {key:'active',label:<button type="button" onClick={noop}><Icon name="xCircle" size={15}/>{t('ai.turn_agent_off')}</button>},
    {key:'delete',label:<button type="button" className="danger" onClick={noop}><Icon name="trash" size={15}/>{t('ai.delete_agent')}</button>},
  ];
  return <header className="agent-head">
    <span className="agent-head-tile" style={{background:tile.background,color:tile.color}}><Icon name="robot" size={28} strokeWidth={1.8}/></span>
    <div className="agent-head-text"><div><h2>{card.name}</h2><b className="agents-status" style={{background:status.bg,color:status.color}}><i/>{status.text}</b></div>
      <p><span><i style={{background:groupColorOf(card.groupId ?? 0,card.groupColor)}}/>{card.groupName}</span><i/><code>{card.code}</code><i/>{openDialogsLine(card.counters.openConversations)}<i/>{t('ai.created_on',{date:createdLabel(card.createdAt)})}</p>
    </div>
    <div className="agent-head-actions">
      <Button variant="secondary" className="agent-test-button" icon="message" disabled aria-expanded={false}>{t('agent_test.open')}</Button>
      <Button variant="secondary" className="agent-toggle" icon="bolt" disabled>{t('ai.start_ai')}</Button>
      <Dropdown menu={{items}} trigger={['click']} overlayClassName="app-dropdown"><button type="button" className="agent-head-menu row-menu-button" aria-label={t('ai.agent_actions')}><Icon name="more" size={17}/></button></Dropdown>
    </div>
  </header>;
}
