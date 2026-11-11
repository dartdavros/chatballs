import { AgentSkillsCard } from "../skills/AgentSkillsCard";
import { AgentActionsCard } from "./actions/AgentActionsCard";
import { Modal } from "antd";
import type { ChannelRoute } from "../../shared/ChannelNavigationMenu";
import { useEffect, useState } from "react";
import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { EmptyState, ErrorScreen, LoadingState } from "../../shared/ui";
import { BackLink } from "../../shared/ui-controls";
import type { EmployeeGroup, RouteKey } from "../../types";
import { AgentToolsCard } from "./AgentToolsCard";
import { enabledToolRefs } from "./agentTools";
import { useAgentDetail } from "./useAgentDetail";
import { AgentHeader } from "./AgentHeader";
import { InstructionsCard } from "./InstructionsCard";
import { KnowledgeCard } from "./KnowledgeCard";
import { AssignmentCard } from "./AssignmentCard";
import { AssistanceCard } from "./AssistanceCard";
import { ConnectionsCard } from "./ConnectionsCard";
import { ModelCard } from "./ModelCard";
import { AgentTestPanel } from "./test-chat/AgentTestPanel";

export function AgentDetailPage({
  agentId,
  groups,
  canManage,
  canManageConnections,
  openAgents,
  openKnowledge,
  openChannels,
  openServers,
  openServer,
  openAiProvider,
  onLoaded,
}: {
  agentId: number | null;
  groups: EmployeeGroup[];
  canManage: boolean;
  canManageConnections: boolean;
  openAgents: () => void;
  openKnowledge: (knowledgeId: number) => void;
  openChannels: (route: ChannelRoute) => void;
  openServers: () => void;
  openServer: (integrationId: number) => void;
  openAiProvider: () => void;
  setRoute: (route: RouteKey) => void;
  onLoaded: (name: string | null) => void;
}) {
  const state = useAgentDetail(agentId, canManage, canManageConnections, openAgents);
  const { card, missing, failed, reload, tools, busy, feedback, deleting, setDeleting, providers, messengers, apply, toggleAi, removeAgent, bind, unbind } = state;
  const [testOpen, setTestOpen] = useState(false);
  useEffect(() => { onLoaded(card?.name ?? null); return () => onLoaded(null); }, [card?.name, onLoaded]);
  if (missing) return <EmptyState title={t("ai.agent_not_found")} />;
  if (failed) return <ErrorScreen retry={() => void reload()} />;
  if (!card) return <LoadingState />;

  const toolsUnsupported = card.modelSupportsTools === false && enabledToolRefs(tools.servers ?? []).length > 0;
  return (
    <div className="agent-page">
      <BackLink label={t("common.agents")} onClick={openAgents} />

      <AgentHeader card={card} canManage={canManage} busy={busy} apply={apply} toggleAi={toggleAi}
        onDelete={() => setDeleting(true)} onTest={() => setTestOpen(true)} testing={testOpen} />

      {card.providerIntegrationId === null && (
        <div className="agent-blocker">
          <Icon name="alert" size={18} strokeWidth={2.2} />
          <div>
            <strong>{t("ai.ai_cannot_reply_no_provider")}</strong>
            <small>{t("ai.add_key_under_settings_ai")}</small>
          </div>
          {canManage && (
            <button type="button" onClick={openAiProvider}>{t("ai.open_settings")}<Icon name="external" size={13} strokeWidth={2.2} /></button>
          )}
        </div>
      )}

      {feedback && <div className={`agent-feedback is-${feedback.kind}`}>{feedback.text}</div>}

      <div className="agent-grid">
        <div className="agent-column">
          <InstructionsCard card={card} canManage={canManage} busy={busy} apply={apply} />
          <ModelCard card={card} providers={providers} canManage={canManage} busy={busy} toolsUnsupported={toolsUnsupported} apply={apply} />
          {canManage && <AgentSkillsCard card={card} />}
          <KnowledgeCard card={card} canManage={canManage} openKnowledge={openKnowledge} reload={reload} />
        </div>
        <div className="agent-column">
          {canManage && <AgentActionsCard key={card.id} agent={card.id} />}
          <AssignmentCard card={card} groups={groups} canManage={canManage} busy={busy} apply={apply} />
          <AssistanceCard key={card.id} card={card} canManage={canManage} busy={busy} save={state.saveAssistance} />
          <ConnectionsCard
            card={card}
            canManage={canManageConnections}
            busy={busy}
            available={messengers.filter((item) => item.channel === null)}
            openChannels={openChannels}
            bind={bind}
            unbind={unbind}
          />
          <AgentToolsCard
            tools={tools}
            modelWarning={toolsUnsupported}
            canManage={canManage}
            canOpenServers={canManageConnections}
            busy={busy}
            save={(refs) => void apply({ tools: refs })}
            openIntegrations={openServers}
            openServer={openServer}
          />
        </div>
      </div>

      {testOpen && <AgentTestPanel key={card.id} card={card} onClose={() => setTestOpen(false)} />}

      {deleting && (
        <Modal
          open
          title={t("ai.delete_agent_2")}
          okText={t("common.delete")}
          cancelText={t("common.cancel")}
          okButtonProps={{ danger: true, disabled: busy }}
          onOk={() => void removeAgent()}
          onCancel={() => setDeleting(false)}
        >
          <p>{t("ai.agent_will_be_deleted", { name: card.name })}</p>
        </Modal>
      )}
    </div>
  );
}
