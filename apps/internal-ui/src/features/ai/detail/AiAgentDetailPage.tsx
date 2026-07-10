import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button, UnderlineTabs } from "../../../shared/ui-controls";
import { AiAgentDetailHeader } from "./AiAgentDetailHeader";
import { AgentEditForm } from "./AgentEditForm";
import { ChannelEditForm } from "./ChannelEditForm";
import { AiAgentInstructionsTab } from "./AiAgentInstructionsTab";
import { AiAgentKnowledgeTab } from "./AiAgentKnowledgeTab";
import { AiAgentMetricsTab } from "./AiAgentMetricsTab";
import { AiAgentOverviewTab } from "./AiAgentOverviewTab";
import { AiAgentReleasesTab } from "./AiAgentReleasesTab";
import { agentTabs, type AgentTab, type AiReleaseFull } from "./model";
import { useAiAgentDetail } from "./useAiAgentDetail";

export function AiAgentDetailPage({ agentId, openRelease, onAgentLoaded }: { agentId: number | null; openRelease: (releaseId: number) => void; onAgentLoaded: (name: string | null) => void }) {
  const { agent, releases, knowledge, prompts, loading, error, reload } = useAiAgentDetail(agentId);
  const [tab, setTab] = useState<AgentTab>("overview");
  const [editOpen, setEditOpen] = useState(false);
  const [channelEdit, setChannelEdit] = useState(false);

  useEffect(() => {
    onAgentLoaded(agent?.name ?? null);
    return () => onAgentLoaded(null);
  }, [agent, onAgentLoaded]);

  async function toggleActive() {
    if (!agent) return;
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    reload();
  }

  async function createRelease() {
    if (!agent) return;
    try {
      const { release } = await api<{ release: AiReleaseFull }>("/api/v1/ai/releases/", { method: "POST", body: JSON.stringify({ channel: agent.channel.code }) });
      reload();
      openRelease(release.id);
    } catch {
      reload();
    }
  }

  if (loading) return <div className="ai-page"><LoadingState /></div>;
  if (error || !agent) return <div className="ai-page"><EmptyState title="Не удалось загрузить агента" /></div>;

  return (
    <div className="ai-agent-page">
      <AiAgentDetailHeader agent={agent} releases={releases} openRelease={openRelease} createRelease={createRelease} onEditChannel={() => setChannelEdit(true)} />
      <UnderlineTabs className="ai-agent-tabs" items={agentTabs} value={tab} onChange={setTab} />
      {(tab === "instructions" || tab === "knowledge") && (
        <div className="ai-notice ai-golive-notice">
          <Icon name="warning" size={17} />
          <span>Изменения вступят в силу после публикации новой версии канала. Опубликуйте release, чтобы выкатить правки в работу.</span>
          <Button variant="primary" icon="bolt" onClick={createRelease}>Создать версию канала</Button>
        </div>
      )}
      {tab === "overview" && <AiAgentOverviewTab agent={agent} toggleActive={toggleActive} onEdit={() => setEditOpen(true)} />}
      {tab === "instructions" && <AiAgentInstructionsTab prompts={prompts} product={agent.channel.product} onChanged={reload} />}
      {tab === "knowledge" && <AiAgentKnowledgeTab knowledge={knowledge} channelName={agent.channel.name} product={agent.channel.product} onChanged={reload} />}
      {tab === "releases" && <AiAgentReleasesTab openRelease={openRelease} releases={releases} />}
      {tab === "metrics" && <AiAgentMetricsTab />}
      {editOpen && <AgentEditForm agent={agent} onClose={() => setEditOpen(false)} onSaved={() => { setEditOpen(false); reload(); }} />}
      {channelEdit && <ChannelEditForm channel={agent.channel} onClose={() => setChannelEdit(false)} onSaved={() => { setChannelEdit(false); reload(); }} />}
    </div>
  );
}
