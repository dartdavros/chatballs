import { AgentConfiguration } from "./AgentConfiguration";
import { Modal } from "antd";
import type { ChannelRoute } from "../../shared/ChannelNavigationMenu";
import { useEffect, useState } from "react";
import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { EmptyState, ErrorScreen, LoadingState } from "../../shared/ui";
import { BackLink } from "../../shared/ui-controls";
import type { EmployeeGroup, RouteKey } from "../../types";
import { enabledToolRefs } from "./agentTools";
import { useAgentDetail } from "./useAgentDetail";
import { AgentHeader } from "./AgentHeader";
import { AgentTestPanel } from "./test-chat/AgentTestPanel";
import { ExternalAgentTestPanel } from "./external/ExternalAgentTestPanel";

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
  openExternalSettings,
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
  openExternalSettings: () => void;
  setRoute: (route: RouteKey) => void;
  onLoaded: (name: string | null) => void;
}) {
  const state = useAgentDetail(agentId, canManage, canManageConnections, openAgents);
  const { card, missing, failed, reload, tools, busy, feedback, deleting, setDeleting, apply, toggleAi, removeAgent } = state;
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
        onDelete={() => setDeleting(true)} onTest={() => setTestOpen(true)} testing={testOpen} testDisabled={card.executionMode === "external" && !card.externalExecution?.available} />

      {card.providerIntegrationId === null && card.executionMode !== "external" && (
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

      <AgentConfiguration card={card} state={state} groups={groups} canManage={canManage} canManageConnections={canManageConnections}
        toolsUnsupported={toolsUnsupported} openKnowledge={openKnowledge} openChannels={openChannels} openServers={openServers}
        openServer={openServer} openExternalSettings={openExternalSettings} />

      {testOpen && (card.executionMode === "external"
        ? <ExternalAgentTestPanel key={card.id} card={card} onClose={() => setTestOpen(false)} />
        : <AgentTestPanel key={card.id} card={card} onClose={() => setTestOpen(false)} />)}

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
