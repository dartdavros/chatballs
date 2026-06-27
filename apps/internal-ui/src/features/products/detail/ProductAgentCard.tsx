import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { productAccent } from "../../../shared/utils";
import { useAiAgents } from "../../ai/useAiAgents";
import type { Product } from "../../../types";

export function ProductAgentCard({ product, openAgentCreate, openAgent }: { product: Product; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void }) {
  const { agents, loading } = useAiAgents();
  const agent = agents.find((item) => item.channel.product?.code === product.code);
  const accent = productAccent(product.code);

  if (loading) {
    return (
      <section className="product-detail-card product-agent-card">
        <h3>Sales-agent</h3>
        <LoadingState variant="inline" />
      </section>
    );
  }

  if (agent) {
    return (
      <section className="product-detail-card product-agent-card">
        <div className="product-agent-heading">
          <span className="product-agent-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="robot" size={17} /></span>
          <div>
            <h3>{agent.name}</h3>
            <p>{agent.model} · {agent.isActive ? "Активен" : "Неактивен"}</p>
          </div>
        </div>
        <Button variant="secondary" className="product-agent-action product-agent-open" onClick={() => openAgent(agent.id)}>Открыть карточку агента</Button>
      </section>
    );
  }

  return (
    <section className="product-detail-card product-agent-card">
      <div className="product-agent-heading">
        <span className="product-agent-icon is-empty"><Icon name="robot" size={17} /></span>
        <div>
          <h3>Sales-agent не создан</h3>
          <p>Создайте агента для этого продукта. Он начнёт работать только после публикации первой версии.</p>
        </div>
      </div>
      <Button variant="primary" className="product-agent-action" icon="plus" onClick={() => openAgentCreate(product.code)}>Создать агента</Button>
    </section>
  );
}
