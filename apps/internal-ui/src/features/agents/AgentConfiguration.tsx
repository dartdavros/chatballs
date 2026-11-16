import type { ChannelRoute } from "../../shared/ChannelNavigationMenu";
import type { EmployeeGroup } from "../../types";
import { AgentSkillsCard } from "../skills/AgentSkillsCard";
import { AgentActionsCard } from "./actions/AgentActionsCard";
import { AgentToolsCard } from "./AgentToolsCard";
import { InstructionsCard } from "./InstructionsCard";
import { KnowledgeCard } from "./KnowledgeCard";
import { ModelCard } from "./ModelCard";
import { AssignmentCard } from "./AssignmentCard";
import { AssistanceCard } from "./AssistanceCard";
import { ConnectionsCard } from "./ConnectionsCard";
import { AgentExecutionCard } from "./external/AgentExecutionCard";
import { ResponseLanguageCard } from "./external/ResponseLanguageCard";
import { SpeechCard } from "./external/SpeechCard";
import type { AgentCard } from "./model";
import type { useAgentDetail } from "./useAgentDetail";
import "../settings/external-agent/styles.css";

export function AgentConfiguration({ card, state, groups, canManage, canManageConnections, toolsUnsupported,
  openKnowledge, openChannels, openServers, openServer, openExternalSettings }: {
  card: AgentCard; state: ReturnType<typeof useAgentDetail>; groups: EmployeeGroup[];
  canManage: boolean; canManageConnections: boolean; toolsUnsupported: boolean;
  openKnowledge: (id: number) => void; openChannels: (route: ChannelRoute) => void; openServers: () => void;
  openServer: (id: number) => void; openExternalSettings: () => void;
}) {
  const external = card.executionMode === "external";
  const { providers, busy, apply, reload, messengers, bind, unbind, tools } = state;
  return <div className="agent-grid"><div className="agent-column">
    <AgentExecutionCard key={`execution-${card.id}`} card={card} canManage={canManage} busy={busy} apply={apply} openSettings={openExternalSettings} />
    {external ? <><ResponseLanguageCard card={card} canManage={canManage} busy={busy} apply={apply} />
      <SpeechCard card={card} providers={providers} canManage={canManage} busy={busy} apply={apply} /></>
      : <><InstructionsCard card={card} canManage={canManage} busy={busy} apply={apply} />
        <ModelCard card={card} providers={providers} canManage={canManage} busy={busy} toolsUnsupported={toolsUnsupported} apply={apply} />
        {canManage && <AgentSkillsCard card={card} />}
        <KnowledgeCard card={card} canManage={canManage} openKnowledge={openKnowledge} reload={reload} /></>}
  </div><div className="agent-column">
    {!external && canManage && <AgentActionsCard key={`actions-${card.id}`} agent={card.id} />}
    <AssignmentCard card={card} groups={groups} canManage={canManage} busy={busy} apply={apply} />
    <AssistanceCard key={`assistance-${card.id}`} card={card} canManage={canManage} busy={busy} save={state.saveAssistance} />
    <ConnectionsCard card={card} canManage={canManageConnections} busy={busy} available={messengers.filter(item => item.channel === null)}
      openChannels={openChannels} bind={bind} unbind={unbind} />
    {!external && <AgentToolsCard tools={tools} modelWarning={toolsUnsupported} canManage={canManage} canOpenServers={canManageConnections}
      busy={busy} save={refs => void apply({ tools: refs })} openIntegrations={openServers} openServer={openServer} />}
  </div></div>;
}
