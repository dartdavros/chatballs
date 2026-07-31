import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { PROVIDERS, STATUS_META, type IntegrationProvider, type IntegrationStatus } from "../../integrations/model";
import type { Product } from "../../../types";

export function ProductChannelsTab({ product, openAgent, openAgentCreate }: { product: Product; openAgent: (agentId: number) => void; openAgentCreate: (productCode: string | null) => void }) {
  const channels = product.channels;

  return (
    <section className="ai-card ai-card--flush">
      <div className="product-channels-head">
        <div>
          <h3>Каналы продаж</h3>
          <div className="product-channels-sub">Через какие каналы обработки продукт доступен клиентам</div>
        </div>
        <Button variant="primary" icon="plus" onClick={() => openAgentCreate(product.code)}>Создать канал</Button>
      </div>

      {channels.length === 0 ? (
        <div className="product-channels-state"><EmptyState title="У продукта пока нет каналов обработки" /></div>
      ) : (
        channels.map((channel) => (
          <div className="product-channel-row" key={channel.id}>
            <span className="product-channel-icon"><Icon name="plug" size={17} /></span>
            <div className="product-channel-info">
              <div className="product-channel-name">{channel.name}</div>
              <div className="product-channel-conns">
                {channel.connections.length === 0 ? <span className="product-channel-empty">Нет подключений</span> : channel.connections.map((connection) => {
                  const status = STATUS_META[connection.status as IntegrationStatus];
                  return (
                    <span className="product-channel-conn" key={connection.id} style={{ background: status.bg, color: status.color }}>
                      {PROVIDERS[connection.provider as IntegrationProvider].label}
                    </span>
                  );
                })}
              </div>
            </div>
            <span className={channel.isActive ? "product-channel-status on" : "product-channel-status off"}>{channel.isActive ? "Активен" : "Выключен"}</span>
            {channel.agentId !== null && (
              <Button variant="secondary" icon="external" onClick={() => openAgent(channel.agentId as number)}>Открыть агента</Button>
            )}
          </div>
        ))
      )}
    </section>
  );
}
