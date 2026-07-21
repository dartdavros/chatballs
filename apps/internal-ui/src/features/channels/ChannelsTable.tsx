import { useState } from "react";

import { Icon } from "../../shared/icons";
import { productAccent } from "../../shared/utils";
import { ChannelBadge } from "./ChannelBadge";
import type { Channel } from "./types";

function AgentCell({ channel, openAgent }: { channel: Channel; openAgent: (agentId: number) => void }) {
  if (!channel.isActive) {
    return (
      <span className="channel-status channel-status--archived">
        <i />
        Архивный
      </span>
    );
  }
  if (!channel.agent) {
    // Канал без агента — валидное операторское состояние, а не ошибка.
    return (
      <div className="channel-agent-empty">
        <span>Нет агента</span>
        <em>операторский канал</em>
      </div>
    );
  }
  const active = channel.agent.status === "ACTIVE";
  return (
    <div className="channel-agent-cell">
      <a
        href="#"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          openAgent(channel.agent!.id);
        }}
      >
        {channel.agent.name}
      </a>
      <span className={`channel-status ${active ? "channel-status--active" : "channel-status--draft"}`}>
        <i />
        {active ? "Активен" : "Черновик"}
      </span>
    </div>
  );
}

export function ChannelsTable({
  channels,
  canManage,
  openChannel,
  openAgent,
  toggleActive,
  footer,
}: {
  channels: Channel[];
  canManage: boolean;
  openChannel: (channelId: number) => void;
  openAgent: (agentId: number) => void;
  toggleActive: (channel: Channel) => Promise<void>;
  footer: string;
}) {
  const [menuId, setMenuId] = useState<number | null>(null);

  return (
    <div className="table-card channels-table-card">
      <table className="baseline-table channels-table">
        <thead>
          <tr>
            <th>КАНАЛ</th>
            <th>ПРОДУКТ</th>
            <th>ПОДКЛЮЧЕНИЯ</th>
            <th>AI-АГЕНТ</th>
            <th className="numeric">ДИАЛОГИ</th>
            <th aria-label="Действия" />
          </tr>
        </thead>
        <tbody>
          {channels.map((channel) => {
            const accent = channel.product ? productAccent(channel.product.code) : null;
            return (
              <tr
                key={channel.id}
                className={channel.isActive ? "" : "is-archived"}
                onClick={() => openChannel(channel.id)}
              >
                <td>
                  <a
                    href="#"
                    className="channel-name"
                    onClick={(event) => {
                      event.preventDefault();
                      openChannel(channel.id);
                    }}
                  >
                    {channel.name}
                  </a>
                  <div className="channel-sub">
                    <code>{channel.code}</code>
                    {" · "}
                    {channel.departmentName ?? <span className="channel-chip">Без отдела</span>}
                  </div>
                </td>
                <td>
                  {channel.product && accent ? (
                    <span
                      className="channel-product-tag"
                      style={{ background: accent.bg, color: accent.color }}
                    >
                      <i style={{ background: accent.color }} />
                      {channel.product.name}
                    </span>
                  ) : (
                    <span className="channel-muted">— непродуктовый</span>
                  )}
                </td>
                <td>
                  {channel.connections.length ? (
                    <span className="channel-badges">
                      {channel.connections.map((connection) => (
                        <ChannelBadge key={connection.id} provider={connection.provider} />
                      ))}
                    </span>
                  ) : (
                    <span className="channel-muted">—</span>
                  )}
                </td>
                <td>
                  <AgentCell channel={channel} openAgent={openAgent} />
                </td>
                <td className="numeric">{channel.counters.openConversations}</td>
                <td className="channel-actions">
                  <button
                    type="button"
                    className={`channel-menu-trigger ${menuId === channel.id ? "is-open" : ""}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      setMenuId(menuId === channel.id ? null : channel.id);
                    }}
                  >
                    <Icon name="more" size={16} />
                  </button>
                  {menuId === channel.id && (
                    <div className="channel-row-menu" onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => {
                          setMenuId(null);
                          openChannel(channel.id);
                        }}
                      >
                        <Icon name="external" size={15} />
                        Открыть
                      </button>
                      {/* Пункты, недоступные по capability, не показываются вовсе. */}
                      {canManage && (
                        <button
                          type="button"
                          className="is-warning"
                          onClick={async () => {
                            setMenuId(null);
                            await toggleActive(channel);
                          }}
                        >
                          <Icon name="pause" size={15} />
                          {channel.isActive ? "Деактивировать" : "Активировать"}
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="channels-table-footer">
        <span>{footer}</span>
        <span>Счётчик «Диалоги» — открытые диалоги канала</span>
      </div>
    </div>
  );
}
