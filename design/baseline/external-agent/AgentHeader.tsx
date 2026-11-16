import { Dropdown } from 'antd';
import { t } from '../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../apps/internal-ui/src/shared/icons';
import { Button } from '../../../apps/internal-ui/src/shared/ui-controls';
import { agentTile, agentStatusMeta, createdLabel, openDialogsLine } from '../../../apps/internal-ui/src/features/agents/model';
import { card } from './design-data';
import { tx } from './copy';

// Current AgentHeader markup; only execution/test availability differs in this proposed state.
export function AgentHeader() {
  const tile = agentTile(card), status = agentStatusMeta(card);
  return <header className="agent-head">
    <span className="agent-head-tile" style={{ background: tile.background, color: tile.color }}>
      <Icon name="robot" size={28} strokeWidth={1.8} /></span>
    <div className="agent-head-text">
      <div><h2>{card.name}</h2><b className="agents-status" style={{ background: status.bg, color: status.color }}><i />{status.text}</b></div>
      <p><span><i style={{ background: card.groupColor }} />{card.groupName}</span><i /><code>{card.code}</code><i />
        {openDialogsLine(0)}<i />{t('ai.created_on', { date: createdLabel(card.createdAt, new Date(card.createdAt)) })}</p>
    </div>
    <div className="agent-head-actions">
      <Button variant="secondary" className="agent-test-button" icon="message" disabled title={tx('unavailable')}>{t('agent_test.open')}</Button>
      <Button variant="secondary" className="agent-toggle" icon="bolt" disabled title={tx('unavailable')}>{t('ai.start_ai')}</Button>
      <Dropdown trigger={['click']} overlayClassName="app-dropdown" menu={{ items: [
        { key: 'active', disabled: true, label: t('ai.turn_agent_off') },
        { key: 'delete', disabled: true, danger: true, label: t('ai.delete_agent') },
      ] }}>
        <button type="button" className="row-menu-button agent-head-menu" aria-label={t('ai.agent_actions')}><Icon name="more" size={17} /></button>
      </Dropdown>
    </div>
  </header>;
}
