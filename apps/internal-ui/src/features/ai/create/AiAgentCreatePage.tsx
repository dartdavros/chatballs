import { useEffect, useMemo, useState } from "react";

import { api } from "../../../api/client";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { fetchKnowledgeList, type KnowledgeItem } from "../knowledge/model";
import { fetchLlmProviders, type Integration } from "../../integrations/model";
import type { CredentialMode } from "../model";
import { useAiAgents } from "../useAiAgents";
import { CreateAgentFooter } from "./CreateAgentFooter";
import { KnowledgeStep } from "./KnowledgeStep";
import { ModelStep } from "./ModelStep";
import { ProductChoiceStep } from "./ProductChoiceStep";
import { PromptStep } from "./PromptStep";
import { startInstructions, startPersona, startTone, type ChannelOption, type CreateAgentResponse } from "./model";

export function AiAgentCreatePage({ selectedProductCode, reload, setRoute, openAgent }: { selectedProductCode: string | null; reload: () => void; setRoute: (route: RouteKey) => void; openAgent: (agentId: number) => void }) {
  const { agents, loading: agentsLoading, reload: reloadAgents } = useAiAgents();
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [channelCode, setChannelCode] = useState<string | null>(selectedProductCode);
  const [credentialMode, setCredentialMode] = useState<CredentialMode>("CUSTOAI");
  const [providerIntegrationId, setProviderIntegrationId] = useState<number | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [persona, setPersona] = useState(startPersona);
  const [tone, setTone] = useState(startTone);
  const [instructions, setInstructions] = useState(startInstructions);
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [selectedKnowledgeIds, setSelectedKnowledgeIds] = useState<number[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    api<{ items: ChannelOption[] }>("/api/v1/channels/")
      .then((payload) => setChannels(payload.items))
      .catch(() => setChannels([]))
      .finally(() => setChannelsLoading(false));
  }, []);

  useEffect(() => {
    fetchLlmProviders().then(setIntegrations).catch(() => setIntegrations([]));
  }, []);

  // Знания — общая библиотека организации (выбор опционален).
  useEffect(() => {
    setKnowledgeLoading(true);
    fetchKnowledgeList()
      .then((payload) => setKnowledge(payload.items))
      .catch(() => setKnowledge([]))
      .finally(() => setKnowledgeLoading(false));
  }, []);

  const agentChannelCodes = useMemo(() => new Set(agents.map((agent) => agent.channel.code)), [agents]);
  const availableChannels = channels.filter((channel) => !agentChannelCodes.has(channel.code));
  const channelsWithAgents = channels.filter((channel) => agentChannelCodes.has(channel.code)).map((channel) => channel.name);
  const selectedChannel = availableChannels.find((channel) => channel.code === channelCode) ?? null;
  const ready = !!selectedChannel && (credentialMode === "CUSTOAI" || providerIntegrationId !== null);

  useEffect(() => {
    if (!channelCode || agentChannelCodes.has(channelCode)) setChannelCode(availableChannels[0]?.code ?? null);
  }, [agentChannelCodes, availableChannels, channelCode]);

  function toggleKnowledge(id: number) {
    setSelectedKnowledgeIds((ids) => ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]);
  }

  async function submit() {
    if (!ready || !selectedChannel) return;
    setSubmitting(true);
    setError(false);
    try {
      const response = await api<CreateAgentResponse>("/api/v1/ai/agents/", {
        method: "POST",
        body: JSON.stringify({ channel: selectedChannel.code, credentialMode, providerIntegrationId, persona, tone, instructions, knowledgeIds: selectedKnowledgeIds }),
      });
      reload();
      reloadAgents();
      if (response.agent) openAgent(response.agent.id);
      else setRoute("aiAgents");
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  const summary = ready && selectedChannel
    ? `Будет создан агент для канала «${selectedChannel.name}» · ${credentialMode === "CUSTOAI" ? "CustoAI" : "BYOK"} · знаний: ${selectedKnowledgeIds.length}. Агент создаётся выключенным — запустите его из карточки.`
    : "Выберите канал без агента, чтобы продолжить.";

  if (agentsLoading || channelsLoading) return <div className="ai-create-page"><LoadingState /></div>;

  return (
    <div className="ai-create-page">
      <div className="ai-create-container">
        <div className="ai-create-header">
          <h1>Создание AI-агента</h1>
          <p>Один агент на канал обработки. Агент создаётся для канала без агента; начнёт отвечать после запуска.</p>
        </div>
        <div className="ai-create-provider">
          <Icon name="check" size={16} />
          {credentialMode === "CUSTOAI" ? "CustoAI · platform credential" : "BYOK · интеграция канала"}
        </div>
        {error && <div className="ai-create-error">Не удалось создать агента. Проверьте выбранный канал.</div>}
        <ProductChoiceStep channels={availableChannels} selectedChannelCode={channelCode} channelsWithAgents={channelsWithAgents} onSelect={setChannelCode} />
        <ModelStep
          credentialMode={credentialMode}
          setCredentialMode={setCredentialMode}
          providerIntegrationId={providerIntegrationId}
          setProviderIntegrationId={setProviderIntegrationId}
          integrations={integrations}
        />
        <PromptStep persona={persona} tone={tone} instructions={instructions} setPersona={setPersona} setTone={setTone} setInstructions={setInstructions} />
        <KnowledgeStep items={knowledge} selectedIds={selectedKnowledgeIds} loading={knowledgeLoading} toggle={toggleKnowledge} />
      </div>
      <CreateAgentFooter summary={summary} ready={ready} submitting={submitting} onCancel={() => setRoute("aiAgents")} onSubmit={submit} />
    </div>
  );
}
