import { useEffect, useMemo, useState } from "react";

import { api } from "../../../api/client";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { useAiAgents } from "../useAiAgents";
import { CreateAgentFooter } from "./CreateAgentFooter";
import { KnowledgeStep } from "./KnowledgeStep";
import { ModelStep } from "./ModelStep";
import { ProductChoiceStep } from "./ProductChoiceStep";
import { PromptStep } from "./PromptStep";
import { startSystemPrompt, type ChannelOption, type CreateAgentResponse, type KnowledgeDocument } from "./model";

export function AiAgentCreatePage({ selectedProductCode, reload, setRoute, openAgent, openRelease }: { selectedProductCode: string | null; reload: () => void; setRoute: (route: RouteKey) => void; openAgent: (agentId: number) => void; openRelease: (releaseId: number) => void }) {
  const { agents, loading: agentsLoading, reload: reloadAgents } = useAiAgents();
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [channelCode, setChannelCode] = useState<string | null>(selectedProductCode);
  const [model, setModel] = useState("anthropic/claude-sonnet-4.6");
  const [systemPrompt, setSystemPrompt] = useState(startSystemPrompt);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument[]>([]);
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

  // Знания — общая библиотека организации (выбор опционален).
  useEffect(() => {
    setKnowledgeLoading(true);
    api<{ items: KnowledgeDocument[] }>("/api/v1/ai/knowledge/")
      .then((payload) => setKnowledge(payload.items.filter((document) => document.versions.length > 0)))
      .catch(() => setKnowledge([]))
      .finally(() => setKnowledgeLoading(false));
  }, []);

  const agentChannelCodes = useMemo(() => new Set(agents.map((agent) => agent.channel.code)), [agents]);
  const availableChannels = channels.filter((channel) => !agentChannelCodes.has(channel.code));
  const channelsWithAgents = channels.filter((channel) => agentChannelCodes.has(channel.code)).map((channel) => channel.name);
  const selectedChannel = availableChannels.find((channel) => channel.code === channelCode) ?? null;
  const ready = !!selectedChannel;

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
        body: JSON.stringify({ channel: selectedChannel.code, model, systemPrompt, knowledgeDocumentIds: selectedKnowledgeIds }),
      });
      reload();
      reloadAgents();
      if (response.agent) openAgent(response.agent.id);
      else if (response.release) openRelease(response.release.id);
      else setRoute("aiAgents");
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  const summary = ready && selectedChannel
    ? `Будет создан агент для канала «${selectedChannel.name}» · модель ${model} · знаний: ${selectedKnowledgeIds.length}. Агент не начнёт отвечать, пока вы не опубликуете первую версию.`
    : "Выберите канал без агента, чтобы продолжить.";

  if (agentsLoading || channelsLoading) return <div className="ai-create-page"><LoadingState /></div>;

  return (
    <div className="ai-create-page">
      <div className="ai-create-container">
        <div className="ai-create-header">
          <h1>Создание AI-агента</h1>
          <p>Один агент на канал обработки. Агент создаётся для канала без агента и начинает работать только после публикации первой версии.</p>
        </div>
        <div className="ai-create-provider"><Icon name="check" size={16} />Модель по умолчанию <b>Sonnet 4.6</b> · провайдер OpenRouter (раздел «Интеграции»)</div>
        {error && <div className="ai-create-error">Не удалось создать агента. Проверьте выбранный канал.</div>}
        <ProductChoiceStep channels={availableChannels} selectedChannelCode={channelCode} channelsWithAgents={channelsWithAgents} onSelect={setChannelCode} />
        <ModelStep model={model} setModel={setModel} />
        <PromptStep systemPrompt={systemPrompt} setSystemPrompt={setSystemPrompt} />
        <KnowledgeStep documents={knowledge} selectedIds={selectedKnowledgeIds} loading={knowledgeLoading} toggle={toggleKnowledge} />
      </div>
      <CreateAgentFooter summary={summary} ready={ready} submitting={submitting} onCancel={() => setRoute("aiAgents")} onSubmit={submit} />
    </div>
  );
}
