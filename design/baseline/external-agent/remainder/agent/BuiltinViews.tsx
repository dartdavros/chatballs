import { t } from '../../../../../apps/internal-ui/src/i18n';
import { Button } from '../../../../../apps/internal-ui/src/shared/ui-controls';
import { InstructionsCard } from '../../../../../apps/internal-ui/src/features/agents/InstructionsCard';
import { ModelCard } from '../../../../../apps/internal-ui/src/features/agents/ModelCard';
import { KnowledgeCard } from '../../../../../apps/internal-ui/src/features/agents/KnowledgeCard';
import { AgentToolsCard } from '../../../../../apps/internal-ui/src/features/agents/AgentToolsCard';
import { SkillsModelWarning } from '../../../../../apps/internal-ui/src/features/skills/SkillsModelWarning';
import '../../../../../apps/internal-ui/src/features/skills/styles';
import '../../../../../apps/internal-ui/src/features/agents/actions/actions.css';
import { builtIn, providers, noop, unchanged } from './data';

export function BuiltinMain() {
  return <>
    <InstructionsCard card={builtIn} canManage busy={false} apply={unchanged} />
    <ModelCard card={builtIn} providers={providers} canManage busy={false} toolsUnsupported={false} apply={unchanged} />
    <section className="agent-card agent-skills-card"><header className="skill-section-head"><div>
      <h3>{t('skills.title')}</h3><p>{t('skills.card_hint')}</p></div>
      <Button variant="secondary" icon="plus" onClick={noop}>{t('skills.connect')}</Button></header>
      <p>{t('skills.none')}</p><SkillsModelWarning support={builtIn.modelSupportsTools}/><div className="skill-notice">{t('skills.shared_hint', { name: builtIn.name })}</div>
    </section>
    <KnowledgeCard card={builtIn} canManage openKnowledge={noop} reload={noop} />
  </>;
}
export function BuiltinActions() {
  return <section className="agent-card is-side agent-actions-card"><h3>{t('agent_actions.title')}</h3>
    <p>{t('agent_actions.description')}</p><Button variant="secondary" onClick={noop}>{t('agent_actions.configure')}</Button></section>;
}
export function BuiltinTools() {
  return <AgentToolsCard tools={{ servers: [], failed: false, reload: noop, adopt: noop }} modelWarning={false}
    canManage canOpenServers busy={false} save={noop} openIntegrations={noop} openServer={noop} />;
}
