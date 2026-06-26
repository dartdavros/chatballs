import { useEffect, useMemo, useState } from "react";

import { api } from "../../../api/client";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import type { Product, RouteKey } from "../../../types";
import { useAiAgents } from "../useAiAgents";
import { CreateAgentFooter } from "./CreateAgentFooter";
import { KnowledgeStep } from "./KnowledgeStep";
import { ModelStep } from "./ModelStep";
import { ProductChoiceStep } from "./ProductChoiceStep";
import { PromptStep } from "./PromptStep";
import { startSystemPrompt, type CreateAgentResponse, type KnowledgeDocument } from "./model";

export function AiAgentCreatePage({ products, selectedProductCode, reload, setRoute, openAgent, openRelease }: { products: Product[]; selectedProductCode: string | null; reload: () => void; setRoute: (route: RouteKey) => void; openAgent: (agentId: number) => void; openRelease: (releaseId: number) => void }) {
  const { agents, loading: agentsLoading, reload: reloadAgents } = useAiAgents();
  const [productCode, setProductCode] = useState<string | null>(selectedProductCode);
  const [model, setModel] = useState("gpt-4o-mini");
  const [systemPrompt, setSystemPrompt] = useState(startSystemPrompt);
  const [knowledge, setKnowledge] = useState<KnowledgeDocument[]>([]);
  const [selectedKnowledgeIds, setSelectedKnowledgeIds] = useState<number[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  const agentProductCodes = useMemo(() => new Set(agents.map((agent) => agent.product.code)), [agents]);
  const availableProducts = products.filter((product) => !agentProductCodes.has(product.code));
  const productsWithAgents = products.filter((product) => agentProductCodes.has(product.code)).map((product) => product.name);
  const selectedProduct = availableProducts.find((product) => product.code === productCode) ?? null;
  const ready = !!selectedProduct && selectedKnowledgeIds.length > 0;

  useEffect(() => {
    if (!productCode || agentProductCodes.has(productCode)) setProductCode(availableProducts[0]?.code ?? null);
  }, [agentProductCodes, availableProducts, productCode]);

  useEffect(() => {
    setSelectedKnowledgeIds([]);
    if (!productCode) {
      setKnowledge([]);
      return;
    }
    setKnowledgeLoading(true);
    api<{ items: KnowledgeDocument[] }>(`/api/v1/ai/knowledge/?product=${encodeURIComponent(productCode)}`)
      .then((payload) => setKnowledge(payload.items.filter((document) => document.versions.length > 0)))
      .catch(() => setKnowledge([]))
      .finally(() => setKnowledgeLoading(false));
  }, [productCode]);

  function toggleKnowledge(id: number) {
    setSelectedKnowledgeIds((ids) => ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id]);
  }

  async function submit() {
    if (!ready || !selectedProduct) return;
    setSubmitting(true);
    setError(false);
    try {
      const response = await api<CreateAgentResponse>("/api/v1/ai/agents/", {
        method: "POST",
        body: JSON.stringify({ product: selectedProduct.code, model, systemPrompt, knowledgeDocumentIds: selectedKnowledgeIds }),
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

  const summary = ready && selectedProduct
    ? `Будет создан агент для «${selectedProduct.name}» · модель ${model} · знаний: ${selectedKnowledgeIds.length}. Агент не начнёт отвечать, пока вы не опубликуете первую версию.`
    : !selectedProduct
      ? "Выберите продукт без агента, чтобы продолжить."
      : "Выберите хотя бы один материал знаний для первой версии.";

  if (agentsLoading) return <div className="ai-create-page"><LoadingState /></div>;

  return (
    <div className="ai-create-page">
      <div className="ai-create-container">
        <div className="ai-create-header">
          <h1>Создание AI-агента</h1>
          <p>Один основной sales-агент на продукт. Агент создаётся для продукта без агента и начинает работать только после публикации первой версии.</p>
        </div>
        <div className="ai-create-provider"><Icon name="check" size={16} />AI-провайдер OpenRouter подключён · модель по умолчанию <b>gpt-4o-mini</b></div>
        {error && <div className="ai-create-error">Не удалось создать агента. Проверьте выбранный продукт и материалы знаний.</div>}
        <ProductChoiceStep products={availableProducts} selectedProductCode={productCode} productsWithAgents={productsWithAgents} onSelect={setProductCode} />
        <ModelStep model={model} setModel={setModel} />
        <PromptStep systemPrompt={systemPrompt} setSystemPrompt={setSystemPrompt} />
        <KnowledgeStep documents={knowledge} selectedIds={selectedKnowledgeIds} loading={knowledgeLoading} toggle={toggleKnowledge} />
      </div>
      <CreateAgentFooter summary={summary} ready={ready} submitting={submitting} onCancel={() => setRoute("aiAgents")} onSubmit={submit} />
    </div>
  );
}
