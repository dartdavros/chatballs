import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { PROVIDERS, STATUS_META } from "../../integrations/model";
import { useProductChannels } from "./channelsApi";

export function ProductChannelsTab({ productCode, openAgent, openAgentCreate }: { productCode: string; openAgent: (agentId: number) => void; openAgentCreate: (productCode: string | null) => void }) {
  const { channels, integrations, loading } = useProductChannels(productCode);

  return (
    <section className="ai-card ai-card--flush">
      <div className="product-channels-head">
        <div>
          <h3>Каналы продаж</h3>
          <div className="product-channels-sub">Через какие каналы обработки продукт доступен клиентам</div>
        </div>
        <Button variant="primary" icon="plus" onClick={() => openAgentCreate(productCode)}>Создать канал</Button>
      </div>

      {loading ? (
        <div className="product-channels-state"><LoadingState /></div>
      ) : channels.length === 0 ? (
        <div className="product-channels-state"><EmptyState title="У продукта пока нет каналов обработки" /></div>
      ) : (
        channels.map((channel) => {
          const connections = integrations.filter((integration) => integration.channel?.id === channel.id);
          return (
            <div className="product-channel-row" key={channel.id}>
              <span className="product-channel-icon"><Icon name="plug" size={17} /></span>
              <div className="product-channel-info">
                <div className="product-channel-name">{channel.name}</div>
                <div className="product-channel-conns">
                  {connections.length === 0 ? <span className="product-channel-empty">Нет подключений</span> : connections.map((connection) => (
                    <span className="product-channel-conn" key={connection.id} style={{ background: STATUS_META[connection.status].bg, color: STATUS_META[connection.status].color }}>
                      {PROVIDERS[connection.provider].label}
                    </span>
                  ))}
                </div>
              </div>
              <span className={channel.isActive ? "product-channel-status on" : "product-channel-status off"}>{channel.isActive ? "Активен" : "Выключен"}</span>
              {channel.agentId !== null && (
                <Button variant="secondary" icon="external" onClick={() => openAgent(channel.agentId as number)}>Открыть агента</Button>
              )}
            </div>
          );
        })
      )}
    </section>
  );
}
